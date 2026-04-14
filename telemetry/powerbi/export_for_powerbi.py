#!/usr/bin/env python3
"""InfluxDB → CSV/Parquet エクスポートスクリプト

InfluxDB に蓄積された走行データを Power BI 用の
4 テーブル（daily_summary, run_sessions, velocity_log, trajectory）に
変換して CSV または Parquet で出力する。

使用例:
    # 直近7日分をCSVでエクスポート（デフォルト）
    python3 export_for_powerbi.py

    # 期間指定 + Parquet形式
    python3 export_for_powerbi.py --start 2026-04-01 --end 2026-04-30 --format parquet

    # ロボットIDフィルタ + 出力先指定
    python3 export_for_powerbi.py --robot-id lightrover_01 --output ./data

環境変数:
    INFLUXDB_TOKEN  認証トークン（--token 引数でも指定可）
"""

import argparse
import math
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas が必要です。pip install pandas を実行してください。", file=sys.stderr)
    sys.exit(1)

from influxdb_client import InfluxDBClient


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SESSION_GAP_SECONDS = 60  # この秒数を超える空白をセッション境界とみなす


# ---------------------------------------------------------------------------
# Flux クエリ定義
# ---------------------------------------------------------------------------

def _flux_velocity_log(bucket: str, start: str, stop: str, robot_filter: str) -> str:
    """velocity_log テーブル用 Flux クエリ（1秒集計）。"""
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r._measurement == "robot_telemetry")
  |> filter(fn: (r) =>
      r._field == "linear_x" or
      r._field == "angular_z" or
      r._field == "speed")
  {robot_filter}
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time", "robot_id"], columnKey: ["_field"], valueColumn: "_value")
'''


def _flux_cmd_vel_log(bucket: str, start: str, stop: str, robot_filter: str) -> str:
    """cmd_vel のログ取得（velocity_log と join 用）。"""
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r._measurement == "cmd_vel")
  |> filter(fn: (r) =>
      r._field == "linear_x" or
      r._field == "angular_z")
  {robot_filter}
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time", "robot_id"], columnKey: ["_field"], valueColumn: "_value")
'''


def _flux_trajectory(bucket: str, start: str, stop: str, robot_filter: str) -> str:
    """trajectory テーブル用 Flux クエリ（500ms集計）。"""
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r._measurement == "robot_telemetry")
  |> filter(fn: (r) =>
      r._field == "pos_x" or
      r._field == "pos_y" or
      r._field == "yaw")
  {robot_filter}
  |> aggregateWindow(every: 500ms, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time", "robot_id"], columnKey: ["_field"], valueColumn: "_value")
'''


def _flux_daily_stats(bucket: str, start: str, stop: str, robot_filter: str) -> str:
    """daily_summary 用: 1日ごとの速度統計。"""
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r._measurement == "robot_telemetry")
  |> filter(fn: (r) => r._field == "speed")
  {robot_filter}
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
'''


# ---------------------------------------------------------------------------
# テーブル生成
# ---------------------------------------------------------------------------

def build_velocity_log(client: InfluxDBClient, bucket: str, org: str,
                       start: str, stop: str, robot_filter: str,
                       query_params: dict) -> pd.DataFrame:
    """velocity_log テーブルを生成する。"""
    query_api = client.query_api()

    # odom データ取得
    odom_df = query_api.query_data_frame(
        _flux_velocity_log(bucket, start, stop, robot_filter), org=org,
        params=query_params
    )
    if isinstance(odom_df, list):
        odom_df = pd.concat(odom_df, ignore_index=True) if odom_df else pd.DataFrame()
    if odom_df.empty:
        return pd.DataFrame()

    # cmd_vel データ取得
    cmd_df = query_api.query_data_frame(
        _flux_cmd_vel_log(bucket, start, stop, robot_filter), org=org,
        params=query_params
    )
    if isinstance(cmd_df, list):
        cmd_df = pd.concat(cmd_df, ignore_index=True) if cmd_df else pd.DataFrame()

    # robot_id がタグとして存在しない場合のフォールバック
    if 'robot_id' not in odom_df.columns:
        odom_df['robot_id'] = 'unknown'

    # odom 列のリネーム
    result = odom_df[['_time', 'robot_id', 'linear_x', 'angular_z', 'speed']].copy()
    result = result.rename(columns={
        '_time': 'timestamp',
        'linear_x': 'odom_linear_x',
        'angular_z': 'odom_angular_z',
    })

    # cmd_vel と結合
    if not cmd_df.empty:
        cmd = cmd_df[['_time', 'robot_id', 'linear_x', 'angular_z']].copy()
        cmd = cmd.rename(columns={
            '_time': 'timestamp',
            'linear_x': 'cmd_linear_x',
            'angular_z': 'cmd_angular_z',
        })
        result = result.merge(cmd, on=['timestamp', 'robot_id'], how='left')
    else:
        result['cmd_linear_x'] = float('nan')
        result['cmd_angular_z'] = float('nan')

    col_order = ['timestamp', 'robot_id', 'cmd_linear_x', 'odom_linear_x',
                 'cmd_angular_z', 'odom_angular_z', 'speed']
    return result[col_order].sort_values('timestamp').reset_index(drop=True)


def build_trajectory(client: InfluxDBClient, bucket: str, org: str,
                     start: str, stop: str, robot_filter: str,
                     query_params: dict) -> pd.DataFrame:
    """trajectory テーブルを生成する。"""
    query_api = client.query_api()
    df = query_api.query_data_frame(
        _flux_trajectory(bucket, start, stop, robot_filter), org=org,
        params=query_params
    )
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return pd.DataFrame()

    if 'robot_id' not in df.columns:
        df['robot_id'] = 'unknown'

    result = df[['_time', 'robot_id', 'pos_x', 'pos_y', 'yaw']].copy()
    result = result.rename(columns={'_time': 'timestamp'})
    result['yaw_deg'] = result['yaw'] * 180.0 / math.pi
    result = result.drop(columns=['yaw'])

    col_order = ['timestamp', 'robot_id', 'pos_x', 'pos_y', 'yaw_deg']
    return result[col_order].sort_values('timestamp').reset_index(drop=True)


def build_daily_summary(client: InfluxDBClient, bucket: str, org: str,
                        start: str, stop: str, robot_filter: str,
                        query_params: dict) -> pd.DataFrame:
    """daily_summary テーブルを生成する。"""
    query_api = client.query_api()
    df = query_api.query_data_frame(
        _flux_daily_stats(bucket, start, stop, robot_filter), org=org,
        params=query_params
    )
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return pd.DataFrame()

    df = df.rename(columns={'_time': 'timestamp', '_value': 'speed'})
    if 'robot_id' not in df.columns:
        df['robot_id'] = 'unknown'
    df['date'] = pd.to_datetime(df['timestamp']).dt.date

    # 日ごと × ロボットごとに集計
    grouped = df.groupby(['date', 'robot_id'])['speed']
    summary = grouped.agg(
        avg_speed_ms='mean',
        max_speed_ms='max',
    ).reset_index()

    # 総走行距離: 1秒ごとの速度を合算（速度×1秒=距離）
    distance = df.groupby(['date', 'robot_id'])['speed'].sum().reset_index()
    distance = distance.rename(columns={'speed': 'total_distance_m'})

    # セッション数: 60秒以上の空白で区切る
    session_counts = []
    for (date, rid), group in df.groupby(['date', 'robot_id']):
        times = pd.to_datetime(group['timestamp']).sort_values()
        gaps = times.diff().dt.total_seconds().fillna(0)
        count = int((gaps > SESSION_GAP_SECONDS).sum()) + 1
        session_counts.append({'date': date, 'robot_id': rid, 'session_count': count})
    sessions_df = pd.DataFrame(session_counts)

    summary = summary.merge(distance, on=['date', 'robot_id'])
    summary = summary.merge(sessions_df, on=['date', 'robot_id'])

    col_order = ['date', 'robot_id', 'session_count', 'total_distance_m',
                 'avg_speed_ms', 'max_speed_ms']
    return summary[col_order].sort_values('date').reset_index(drop=True)


def build_run_sessions(velocity_log: pd.DataFrame) -> pd.DataFrame:
    """velocity_log から走行セッションを抽出する。

    セッション定義: 60秒以上のデータ空白で区切られた走行区間。
    """
    if velocity_log.empty:
        return pd.DataFrame()

    sessions = []
    for rid, group in velocity_log.groupby('robot_id'):
        group = group.sort_values('timestamp')
        times = pd.to_datetime(group['timestamp'])
        gaps = times.diff().dt.total_seconds().fillna(0)

        # SESSION_GAP_SECONDS 秒超の空白をセッション境界とする
        session_ids = (gaps > SESSION_GAP_SECONDS).cumsum()

        for _, session_group in group.assign(_sid=session_ids).groupby('_sid'):
            ts = pd.to_datetime(session_group['timestamp'])
            start_time = ts.min()
            end_time = ts.max()
            duration_s = (end_time - start_time).total_seconds()

            speed_vals = session_group['speed'].fillna(0)
            distance_m = speed_vals.sum()  # 1秒ごとの速度 × 1秒
            avg_speed = speed_vals.mean()

            # 追従誤差 RMS
            lin_diff = session_group['cmd_linear_x'].fillna(0) - session_group['odom_linear_x'].fillna(0)
            ang_diff = session_group['cmd_angular_z'].fillna(0) - session_group['odom_angular_z'].fillna(0)
            tracking_error_linear = math.sqrt((lin_diff ** 2).mean()) if len(lin_diff) > 0 else 0.0
            tracking_error_angular = math.sqrt((ang_diff ** 2).mean()) if len(ang_diff) > 0 else 0.0

            sessions.append({
                'session_id': str(uuid.uuid4()),
                'robot_id': rid,
                'start_time': start_time,
                'end_time': end_time,
                'duration_s': round(duration_s, 1),
                'distance_m': round(distance_m, 3),
                'avg_speed_ms': round(avg_speed, 4),
                'tracking_error_linear': round(tracking_error_linear, 4),
                'tracking_error_angular': round(tracking_error_angular, 4),
            })

    return pd.DataFrame(sessions)


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def save_table(df: pd.DataFrame, name: str, output_dir: Path, fmt: str) -> None:
    """DataFrame を指定フォーマットでファイルに保存する。"""
    if df.empty:
        print(f"  {name}: データなし（スキップ）")
        return

    if fmt == 'parquet':
        path = output_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
    else:
        path = output_dir / f"{name}.csv"
        df.to_csv(path, index=False)

    print(f"  {name}: {len(df)} 行 → {path}")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description='InfluxDB の走行データを Power BI 用 CSV/Parquet にエクスポート'
    )
    parser.add_argument('--start', type=str, default=None,
                        help='開始日 ISO8601（デフォルト: 7日前）')
    parser.add_argument('--end', type=str, default=None,
                        help='終了日 ISO8601（デフォルト: 今日）')
    parser.add_argument('--robot-id', type=str, default=None,
                        help='フィルタするrobot_id（省略で全ロボット）')
    parser.add_argument('--format', type=str, choices=['csv', 'parquet'], default='csv',
                        help='出力フォーマット（デフォルト: csv）')
    parser.add_argument('--output', type=str, default='./export',
                        help='出力ディレクトリ（デフォルト: ./export）')
    parser.add_argument('--url', type=str, default='http://localhost:8086',
                        help='InfluxDB URL')
    parser.add_argument('--token', type=str, default=None,
                        help='InfluxDB トークン（デフォルト: $INFLUXDB_TOKEN）')
    parser.add_argument('--org', type=str, default='lightrover',
                        help='InfluxDB 組織名（デフォルト: lightrover）')
    parser.add_argument('--bucket', type=str, default='seminar',
                        help='InfluxDB バケット名（デフォルト: seminar）')
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # デフォルト日時の設定
    now = datetime.now(timezone.utc)
    if args.start is None:
        start_dt = now - timedelta(days=7)
    else:
        start_dt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    if args.end is None:
        end_dt = now
    else:
        end_dt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    stop_str = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    # robot_id フィルタ（パラメータバインディングでインジェクション防止）
    robot_filter = ''
    query_params = {}
    if args.robot_id:
        robot_filter = '|> filter(fn: (r) => r.robot_id == params.robot_id)'
        query_params = {"robot_id": args.robot_id}

    # トークン取得
    token = args.token or os.environ.get('INFLUXDB_TOKEN', '')
    if not token:
        print("Error: --token または INFLUXDB_TOKEN 環境変数が必要です。", file=sys.stderr)
        sys.exit(1)

    # 出力ディレクトリ作成
    date_str = now.strftime('%Y%m%d')
    output_dir = Path(args.output) / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"InfluxDB エクスポート")
    print(f"  URL:    {args.url}")
    print(f"  期間:   {start_str} 〜 {stop_str}")
    print(f"  形式:   {args.format}")
    print(f"  出力先: {output_dir}")
    print()

    # InfluxDB 接続
    client = InfluxDBClient(url=args.url, token=token, org=args.org)

    try:
        # 1. velocity_log（他テーブルの基礎データ）
        print("velocity_log を取得中...")
        velocity_log = build_velocity_log(
            client, args.bucket, args.org, start_str, stop_str, robot_filter, query_params
        )
        save_table(velocity_log, 'velocity_log', output_dir, args.format)

        # 2. trajectory
        print("trajectory を取得中...")
        trajectory = build_trajectory(
            client, args.bucket, args.org, start_str, stop_str, robot_filter, query_params
        )
        save_table(trajectory, 'trajectory', output_dir, args.format)

        # 3. daily_summary
        print("daily_summary を取得中...")
        daily_summary = build_daily_summary(
            client, args.bucket, args.org, start_str, stop_str, robot_filter, query_params
        )
        save_table(daily_summary, 'daily_summary', output_dir, args.format)

        # 4. run_sessions（velocity_log から導出）
        print("run_sessions を算出中...")
        run_sessions = build_run_sessions(velocity_log)
        save_table(run_sessions, 'run_sessions', output_dir, args.format)

    finally:
        client.close()

    print()
    print("エクスポート完了。")


if __name__ == '__main__':
    main()
