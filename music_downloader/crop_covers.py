from pathlib import Path

import cv2
import numpy as np

MUSIC_PATH = Path().home() / "Musique"


def crop_edges(image_path: Path, overwrite: bool = False) -> None:
    print(f"Cropping {image_path}")
    image = cv2.imread(str(image_path))

    y_nonzero, x_nonzero, _ = np.nonzero(image)
    crop = image[
        np.min(y_nonzero) : np.max(y_nonzero), np.min(x_nonzero) : np.max(x_nonzero)
    ]

    new_path = image_path if overwrite else image_path.with_stem("cropped")
    cv2.imwrite(str(new_path), crop)


def main():
    for path in MUSIC_PATH.glob("**/*.jpg"):
        try:
            crop_edges(Path(path))
        except ValueError:
            print(f"{path} cannot be opened")


if __name__ == "__main__":
    main()
