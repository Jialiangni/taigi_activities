"""Build the public calendar from reviewed, traceable sessions only."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from build_html import generate_single_html
from crawler.sources.google_workspace import GoogleWorkspaceSync
from crawler.verified import load_verified
from crawler.resources import load_resources


def build(output_dir=Path('.'), check_sources=False):
    # Validate every record/source before replacing any existing artifact.
    activities = load_verified(check_sources=check_sources)
    resources = load_resources(check_sources=check_sources)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as stage:
        stage = Path(stage)
        calendar = GoogleWorkspaceSync()
        calendar.export_ics(activities, stage / 'taigi_activities.ics')
        event_dir = stage / 'calendar-events'
        event_dir.mkdir()
        for activity in activities:
            calendar.export_ics([activity], event_dir / calendar.single_event_filename(activity))
        generate_single_html(activities, stage / 'index.html', resources=resources)
        (stage / 'taigi-activities-standalone.html').write_bytes((stage / 'index.html').read_bytes())
        # Replace the generated set only after all validation/build steps succeeded.
        # This removes stale single-event files without touching source records.
        target = output_dir / 'calendar-events'
        backup = stage / 'previous-calendar-events'
        if target.exists():
            target.replace(backup)
        try:
            event_dir.replace(target)
        except Exception:
            if backup.exists():
                backup.replace(target)
            raise
        for name in ('index.html', 'taigi_activities.ics', 'taigi-activities-standalone.html'):
            (stage / name).replace(output_dir / name)
    print(f'已產生 {len(activities)} 筆經核實、尚未結束的場次。')
    print(f'另列 {len(resources)} 項導覽／展覽／閱讀／傳統表演資訊，不計入場次或 ICS。')
    print('核實日期見個別活動；建置不會自動新增或認證活動。')
    return activities


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-sources', action='store_true', help='重查公告必要內容；失敗則停止建置')
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    build(args.output_dir, args.check_sources)
