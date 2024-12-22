import time
import subprocess
from pathlib import Path
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def convert_md_to_docx(markdown_file, docx_file):
    print(f"Syncing '{markdown_file}' to '{docx_file}'.")
    subprocess.run(["pandoc", str(markdown_file), "-o", str(docx_file)])


def convert_docx_to_md(docx_file, markdown_file):
    print(f"Syncing '{docx_file}' to '{markdown_file}'.")
    subprocess.run(["pandoc", str(docx_file), "-o", str(markdown_file)])


TIME_DELTA = 10  # seconds


class FileSyncHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_sync_time = {}  # Prevents infinite loops during syncs, per file

    def sync_files(self, markdown_file, docx_file):
        current_time = time.time()
        last_sync = self.last_sync_time.get(markdown_file, 0)

        if not docx_file.exists():
            print(
                f"Docx file '{docx_file}' does not exist. Creating it from '{markdown_file}'."
            )
            convert_md_to_docx(markdown_file, docx_file)
            self.last_sync_time[markdown_file] = current_time
            return

        md_mtime = markdown_file.stat().st_mtime
        docx_mtime = docx_file.stat().st_mtime

        # print(f"time diff: {md_mtime - docx_mtime}")
        # Sync logic with debouncing
        if (md_mtime - docx_mtime) > TIME_DELTA and (current_time - last_sync) > 1:
            convert_md_to_docx(markdown_file, docx_file)
            self.last_sync_time[markdown_file] = current_time
        elif (docx_mtime - md_mtime) > TIME_DELTA and (current_time - last_sync) > 1:
            convert_docx_to_md(docx_file, markdown_file)
            self.last_sync_time[markdown_file] = current_time

    def on_created(self, event):
        path = Path(event.src_path)
        # print("created ", path)
        if path.suffix == ".md":
            docx_file = path.with_suffix(".docx")
            self.sync_files(path, docx_file)
        elif path.suffix == ".docx":
            markdown_file = path.with_suffix(".md")
            self.sync_files(markdown_file, path)

    def on_modified(self, event):
        path = Path(event.src_path)
        # print("modified ", path)
        if path.suffix == ".md":
            docx_file = path.with_suffix(".docx")
            self.sync_files(path, docx_file)
        elif path.suffix == ".docx":
            markdown_file = path.with_suffix(".md")
            if markdown_file.exists():
                self.sync_files(markdown_file, path)

    # def on_moved(self, event):
    #     print("moved ", event.src_path, " to ", event.dest_path)


def monitor_directory(directory):
    directory_path = Path(directory)

    if not directory_path.exists():
        raise FileNotFoundError(f"Directory '{directory}' does not exist.")

    event_handler = FileSyncHandler()
    observer = Observer()
    observer.schedule(event_handler, str(directory_path), recursive=False)

    print(f"Monitoring Markdown and Docx files in '{directory}' for changes.")
    observer.start()

    try:
        while True:
            time.sleep(TIME_DELTA)
            for file in directory_path.iterdir():
                if file.suffix == ".md":
                    docx_file = file.with_suffix(".docx")
                    event_handler.sync_files(file, docx_file)
                elif file.suffix == ".docx":
                    markdown_file = file.with_suffix(".md")
                    event_handler.sync_files(markdown_file, file)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pandoc_sync.py <directory>")
        sys.exit(1)

    monitor_directory(sys.argv[1])
