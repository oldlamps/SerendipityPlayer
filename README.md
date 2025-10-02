# Serendipity Player


## About

An mpv video player frontend for rediscovering your local media library through random, short clips.

## About The Project

Do you have a massive library of movies and TV shows sitting on a hard drive? Serendipity Player helps you rediscover those forgotten gems by playing continuous, random clips from your entire collection.

Instead of endlessly scrolling through file names, just launch the app and let it surprise you. It will jump from a random 30-90 second scene in one file to another completely different moment in the next, creating a unique and relaxing viewing experience. If a particular scene catches your interest, you can "lock" it to watch the rest of the file from that point on.

It's like channel surfing for your own personal video archive.

## Features

  * **Random Clip Generation**: Automatically plays random 30-90 second clips from your video library.
  * **Seamless Playback**: When one clip ends, the next one begins automatically.
  * **Lock and Continue**: See a scene you like? Lock the video to disable the clip timer and watch the rest of the file. The player will return to random mode when the file ends.
  * **External Configuration**: Easily change your library path, clip duration, and supported file types via a `settings.json` file.
  * **Full Keyboard Control**:
      * `Space`: Play/Pause
      * `f`: Toggle Fullscreen
      * `l`: Lock/Unlock the current video
      * `n`: Skip to the next random clip
      * `m`: Toggle mute (auto-enables subtitles if available)
      * `s`: Manually toggle subtitles
  * **Embedded MPV**: Uses the powerful and highly compatible `mpv` player engine, embedded within a clean GTK3 interface.

## Getting Started

To get a local copy up and running, follow these steps.

### Prerequisites

You will need `mpv`, `python3`, `pip`, and the GTK3 development libraries installed on your system.

  * **mpv player**
    ```sh
    # On Debian/Ubuntu
    sudo apt-get install mpv
    ```
  * **Python Libraries**
    ```sh
    pip install python-mpv PyGObject
    ```
  
### Installation & Running

1.  Clone the repo:
    ```sh
    git clone https://github.com/oldlamps/SerendipityPlayer.git
    ```
2.  Navigate to the directory:
    ```sh
    cd SerendipityPlayer
    ```
3.  Run the application:
    ```sh
    python serendipity-player.py
    ```
4.  On the first run, click the settings icon (⚙) to choose the folder containing your video library.

## Configuration

The application's settings are stored in a `settings.json` file located in your user's configuration directory (e.g., `~/.config/serendipity-player/settings.json` on Linux). You can edit this file to change the behavior of the player.

```json
{
    "video_library_path": "/path/to/your/videos",
    "min_clip_duration": 30,
    "max_clip_duration": 90,
    "supported_extensions": [
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".webm",
        ".flv"
    ]
}
```
