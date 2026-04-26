import tkinter as tk

from src.app import OCRApp


def main() -> None:
    root = tk.Tk()
    OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
