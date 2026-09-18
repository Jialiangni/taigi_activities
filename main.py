"""Build the public calendar from reviewed, traceable sessions only."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from build_html import generate_single_html
from crawler.sources.google_workspace import GoogleWorkspaceSync
from crawler.verified import load_verified


def build(output_dir=Path('.'), check_sources=False):
    # Validate every record/source before replacing any existing artifact.
    activities = load_verified(check_sources=check_sources)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as stage:
        stage = Path(stage)
        GoogleWorkspaceSync().export_ics(activities, stage / 'taigi_activities.ics')
        generate_single_html(activities, stage / 'index.html')
        for name in ('index.html', 'taigi_activities.ics'):
            (stage / name).replace(output_dir / name)
    print(f'已產生 {len(activities)} 筆經人工核實、尚未結束的場次。')
    print('核實日期見個別活動；建置不會自動新增或認證活動。')
    return activities


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-sources', action='store_true', help='重查公告必要內容；失敗則停止建置')
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    build(args.output_dir, args.check_sources)
