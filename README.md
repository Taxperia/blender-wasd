# GameNav

GameNav is a standalone Blender extension for navigating the 3D Viewport with familiar game-style controls. It is designed for large architectural scenes, environments, and other projects where orbiting, panning, and zooming can become cumbersome.

## Features

- Move with `W A S D` or the arrow keys
- Look around freely with the mouse
- Move up and down with `E / Q`
- Hold `Shift` to sprint or `Alt` for precise movement
- Adjust speed during navigation with the mouse wheel
- Room, Scene, and Mega speed presets
- Optional horizontal WASD movement
- Smooth acceleration and deceleration
- Quickly focus on the selected object
- Extended viewport clipping for very large scenes
- Save a home view inside the `.blend` file
- Configurable `Shift + F` shortcut

## Requirements

- Blender 4.2 or newer

## Installation

1. Download the latest `gamenav-*.zip` package.
2. In Blender, open **Edit > Preferences > Extensions**.
3. Open the menu in the top-right corner and choose **Install from Disk**.
4. Select the ZIP file and enable GameNav.
5. In the 3D Viewport, press `N` and open the **GameNav** tab.

## Usage

With the cursor over the 3D Viewport, press `Shift + F` or click **WASD Gezinmeyi Başlat** in the GameNav panel.

| Control | Action |
| --- | --- |
| `W A S D` / Arrow keys | Move |
| Mouse | Look around |
| `E / Q` | Move up / down |
| `Shift` | Sprint |
| `Alt` | Move slowly and precisely |
| Mouse wheel | Increase / decrease movement speed |
| Left click / `Enter` | Keep the new view and exit |
| `Esc` / Right click | Restore the starting view and exit |

To change the shortcut, open **Edit > Preferences > Keymap** and search for `GameNav` or `GameNav Başlat`.

## Build from Source

The repository root contains both `__init__.py` and `blender_manifest.toml`. Build an installable extension package with Blender's command-line interface:

```text
blender --command extension build
```

## License

GameNav is licensed under the GPL-3.0-or-later license. See [LICENSE](LICENSE) for details.
