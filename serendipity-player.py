import os
os.environ['GDK_BACKEND'] = 'x11'

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import mpv
import random
import sys
import json

class SettingsDialog(Gtk.Dialog):
    """A dialog to choose the video library folder."""
    def __init__(self, parent, current_path):
        super().__init__(title="Settings", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        self.set_default_size(500, 100)
        self.path = current_path
        box = self.get_content_area()
        grid = Gtk.Grid(margin=10, column_spacing=10, row_spacing=10)
        box.add(grid)
        label = Gtk.Label(label="Video Library Path:")
        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(self.path)
        self.path_entry.set_hexpand(True)
        browse_button = Gtk.Button(label="Browse...")
        browse_button.connect("clicked", self.on_browse_clicked)
        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.path_entry, 1, 0, 1, 1)
        grid.attach(browse_button, 2, 0, 1, 1)
        self.show_all()

    def on_browse_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.path = dialog.get_filename()
            self.path_entry.set_text(self.path)
        dialog.destroy()
    
    def get_path(self):
        return self.path_entry.get_text()

class MpvPlayerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Seredipity Clip Player")
        self.set_default_size(1280, 720)
        self.connect("destroy", Gtk.main_quit)

        self.is_fullscreen = False
        self.subtitles_auto_enabled = False
        self.is_locked = False
        self.is_changing_clip = False
        self.config_dir = os.path.join(GLib.get_user_config_dir(), 'serendipity-player')
        self.config_file = os.path.join(self.config_dir, 'settings.json')
        self.load_settings()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.drawing_area.connect("button-press-event", self.on_drawing_area_clicked)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        vbox.pack_start(self.drawing_area, True, True, 0)
        self.control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.control_box.set_halign(Gtk.Align.CENTER)
        style_context = self.control_box.get_style_context()
        css_provider = Gtk.CssProvider()
        css = b"""
        box { background-color: rgba(20, 20, 20, 0.85); padding: 5px; }
        button { color: white; background: transparent; border: none; font-size: 24px; }
        """
        css_provider.load_from_data(css)
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.play_pause_button = Gtk.Button.new_with_label("⏸")
        self.play_pause_button.connect("clicked", self.on_toggle_pause)
        self.control_box.pack_start(self.play_pause_button, False, False, 5)
        self.next_button = Gtk.Button.new_with_label("⏩")
        self.next_button.connect("clicked", self.on_next_clicked)
        self.control_box.pack_start(self.next_button, False, False, 5)
        self.lock_button = Gtk.Button.new_with_label("🔓")
        self.lock_button.connect("clicked", self.on_toggle_lock)
        self.control_box.pack_start(self.lock_button, False, False, 5)
        self.fullscreen_button = Gtk.Button.new_with_label("⛶")
        self.fullscreen_button.connect("clicked", self.on_toggle_fullscreen)
        self.control_box.pack_start(self.fullscreen_button, False, False, 5)
        self.settings_button = Gtk.Button.new_with_label("⚙")
        self.settings_button.connect("clicked", self.on_open_settings)
        self.control_box.pack_start(self.settings_button, False, False, 5)
        vbox.pack_start(self.control_box, False, True, 0)
        self.connect("key-press-event", self.on_key_press)
        self.player = None
        self.video_files = self.scan_video_library()
        self.last_played_file = None
        if not self.video_files:
            dialog = Gtk.MessageDialog(
                transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK, text=f"No video files found in '{self.video_library_path}'"
            )
            dialog.format_secondary_text("Please select a valid directory in the settings (⚙).")
            dialog.run()
            dialog.destroy()
        self.drawing_area.connect("realize", self.on_realize)

    def on_drawing_area_clicked(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.on_toggle_fullscreen(None)
            return True
        return False

    def load_settings(self):
        self.video_library_path = os.path.expanduser('~/Videos')
        self.min_clip_duration = 30
        self.max_clip_duration = 90
        self.supported_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.video_library_path = config.get('video_library_path', self.video_library_path)
                self.min_clip_duration = config.get('min_clip_duration', self.min_clip_duration)
                self.max_clip_duration = config.get('max_clip_duration', self.max_clip_duration)
                self.supported_extensions = config.get('supported_extensions', self.supported_extensions)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read settings file at {self.config_file}. Using defaults.")
        else:
            self.save_settings()

    def save_settings(self):
        os.makedirs(self.config_dir, exist_ok=True)
        config = {
            'video_library_path': self.video_library_path,
            'min_clip_duration': self.min_clip_duration,
            'max_clip_duration': self.max_clip_duration,
            'supported_extensions': self.supported_extensions
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def on_open_settings(self, widget):
        dialog = SettingsDialog(self, self.video_library_path)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialog.get_path()
            if new_path != self.video_library_path and os.path.isdir(new_path):
                print(f"Library path changed to: {new_path}")
                self.video_library_path = new_path
                self.save_settings()
                if self.player:
                    self.player.stop()
                self.video_files = self.scan_video_library()
                if self.video_files and self.player:
                    self.play_random_clip()
                elif not self.video_files:
                     dialog = Gtk.MessageDialog(
                        transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK, text=f"No video files found in '{self.video_library_path}'"
                    )
                     dialog.run()
                     dialog.destroy()
        dialog.destroy()

    def on_end_file(self, event):
        """Callback for when a file finishes playing."""
        # This debug line will show us the exact reason mpv gives us
        print(f"DEBUG: end-file event received. Reason: '{str(event.data.reason)}'")
        
        # Using str() makes this check compatible with older and newer python-mpv versions.
        if str(event.data.reason) == '0':
            GLib.idle_add(self._handle_end_of_file)

    def _handle_end_of_file(self):
        if self.is_changing_clip: return GLib.SOURCE_REMOVE
        if self.is_locked:
            print("Locked video finished. Unlocking and playing next clip.")
            self.is_locked = False
            self.lock_button.set_label("🔓")
        else:
            print("File finished. Playing next clip.")
        self.play_random_clip()
        return GLib.SOURCE_REMOVE

    def on_realize(self, widget):
        def mpv_log(level, prefix, text):
            print(f'[mpv {level}] {prefix}: {text.strip()}', file=sys.stderr)
        if self.player: return
        try:
            gdk_window = self.drawing_area.get_window()
            wid = str(gdk_window.get_xid())
            self.player = mpv.MPV(
                wid=wid, vo='x11', log_handler=mpv_log,
                input_default_bindings=True, input_vo_keyboard=True
            )
            self.player.observe_property('time-pos', self.on_time_pos_change)
            @self.player.event_callback('end-file')
            def end_file_handler(event):
                self.on_end_file(event)
            print("mpv player initialized and embedded.")
            if self.video_files:
                GLib.idle_add(self.play_random_clip)
        except Exception as e:
            print(f"Fatal Error initializing mpv: {e}", file=sys.stderr)
            Gtk.main_quit()

    def scan_video_library(self):
        files = []
        if not os.path.isdir(self.video_library_path):
            print(f"Error: Library path '{self.video_library_path}' does not exist.", file=sys.stderr)
            return files
        print(f"Scanning for videos in: {self.video_library_path}")
        for root, _, filenames in os.walk(self.video_library_path):
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in self.supported_extensions):
                    files.append(os.path.join(root, filename))
        print(f"Found {len(files)} video files.")
        return files

    def on_next_clicked(self, widget):
        if self.is_changing_clip: return
        if self.is_locked:
            self.is_locked = False
            self.lock_button.set_label("🔓")
            self.player.command('show-text', 'Video Unlocked', 2000)
        self.play_random_clip()
    
    def on_toggle_lock(self, widget):
        if not self.player or not self.player.path:
            return
        self.is_locked = not self.is_locked
        self.lock_button.set_label("🔒" if self.is_locked else "🔓")
        if self.is_locked:
            self.player.command('show-text', 'Video Locked', 2000)
            print("Video locked. Will play to end.")
        else:
            if self.is_changing_clip: return
            self.player.command('show-text', 'Video Unlocked', 2000)
            print("Video unlocked. Playing new random clip.")
            self.play_random_clip()

    def on_toggle_pause(self, widget):
        if self.player:
            self.player.pause = not self.player.pause
            self.play_pause_button.set_label("▶" if self.player.pause else "⏸")

    def on_toggle_fullscreen(self, widget):
        if self.is_fullscreen:
            self.unfullscreen()
            self.control_box.show()
        else:
            self.fullscreen()
            self.control_box.hide()
        self.is_fullscreen = not self.is_fullscreen
        
    def on_key_press(self, widget, event):
        keyval = event.keyval
        if keyval == Gdk.KEY_space:
            self.on_toggle_pause(None)
            return True
        elif self.is_fullscreen and keyval == Gdk.KEY_Escape:
            self.on_toggle_fullscreen(None)
            return True
        elif keyval == Gdk.KEY_f:
            self.on_toggle_fullscreen(None)
            return True
        elif keyval == Gdk.KEY_l:
            self.on_toggle_lock(None)
            return True
        elif keyval == Gdk.KEY_n:
            self.on_next_clicked(None)
            return True
        elif keyval == Gdk.KEY_m:
            if not self.player: return True
            self.player.mute = not self.player.mute
            print(f"Mute: {self.player.mute}")
            if self.player.mute:
                if not self.player.sid and self.player.track_list:
                    sub_tracks = [t for t in self.player.track_list if t.get('type') == 'sub']
                    if sub_tracks:
                        self.player.sid = sub_tracks[0]['id']
                        self.subtitles_auto_enabled = True
                        print("Muted. Auto-enabled subtitles.")
            else:
                if self.subtitles_auto_enabled:
                    self.player.sid = 0
                    self.subtitles_auto_enabled = False
                    print("Unmuted. Auto-disabled subtitles.")
            return True
        elif keyval == Gdk.KEY_s:
            if not self.player: return True
            if self.player.sid:
                self.player.sid = 0
                self.subtitles_auto_enabled = False
                print("Subtitles manually disabled.")
            else:
                if self.player.track_list:
                    sub_tracks = [t for t in self.player.track_list if t.get('type') == 'sub']
                    if sub_tracks:
                        self.player.sid = sub_tracks[0]['id']
                        self.subtitles_auto_enabled = False
                        print("Subtitles manually enabled.")
                    else:
                        print("No subtitle tracks found.")
            return True
        return False

    def play_random_clip(self):
        if self.is_changing_clip: return
        self.is_changing_clip = True
        try:
            if not self.video_files or self.player is None:
                return
            available_files = [f for f in self.video_files if f != self.last_played_file]
            if not available_files:
                available_files = self.video_files
            chosen_file = random.choice(available_files)
            self.last_played_file = chosen_file
            self.subtitles_auto_enabled = False
            self.player.loadfile(chosen_file, 'replace')
            self.player.wait_for_property('duration')
            duration = self.player.duration
            if duration is None or duration <= self.min_clip_duration:
                start_pos = 0
                self.end_pos = duration + 1 if duration else 99999
                print(f"Video is short, playing entire file.")
            else:
                actual_max_clip = min(self.max_clip_duration, duration)
                clip_duration = random.uniform(self.min_clip_duration, actual_max_clip)
                max_start_pos = duration - clip_duration
                start_pos = random.uniform(0, max_start_pos)
                self.end_pos = start_pos + clip_duration
            self.player.seek(start_pos, 'absolute')
            self.player.pause = False
            self.play_pause_button.set_label("⏸")
            filename = os.path.basename(chosen_file)
            self.set_title(f"Serendipity Clip Player - {filename}")
            print(f"Playing '{filename}'. Start: {start_pos:.2f}s, End: {self.end_pos:.2f}s")
        finally:
            self.is_changing_clip = False
        return GLib.SOURCE_REMOVE
    
    def on_time_pos_change(self, name, value):
        GLib.idle_add(self._check_clip_end, value)

    def _check_clip_end(self, current_pos):
        if self.is_locked or self.is_changing_clip:
            return GLib.SOURCE_REMOVE
        if current_pos is not None and hasattr(self, 'end_pos'):
            if current_pos >= self.end_pos:
                print("Clip finished. Playing next one.")
                self.play_random_clip()
        return GLib.SOURCE_REMOVE

def main():
    win = MpvPlayerWindow()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()