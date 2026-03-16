"""
Yaapt — Yet Again Another Plotting Terminal
Entry point: python yaapt.py
"""

from gui import YaaptApplication


def main():
    app = YaaptApplication()
    app.exec()


if __name__ == '__main__':
    main()
