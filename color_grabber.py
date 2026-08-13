#!/usr/bin/env python3
import os
import sys
import objc
import webview
from AppKit import NSStatusBar, NSVariableStatusItemLength
from Foundation import NSObject
from PyObjCTools import AppHelper


class StatusBarDelegate(NSObject):
    controller = objc.ivar()

    @objc.IBAction
    def onIconClick_(self, sender):
        AppHelper.callAfter(self.controller.toggle_visibility)


class ColorGrabberController:
    def __init__(self):
        self.window = None
        self.is_visible = False
        self.delegate = None
        self.status_bar = None
        self.status_item = None

    def bind_window(self, window):
        self.window = window

    def initialize_menu_bar(self):
        self.delegate = StatusBarDelegate.alloc().init()
        self.delegate.controller = self

        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        
        self.status_item.button().setTitle_("🎨")
        self.status_item.button().setTarget_(self.delegate)
        self.status_item.button().setAction_(objc.selector(self.delegate.onIconClick_, signature=b'v@:@'))

    def toggle_visibility(self):
        if self.is_visible:
            self.hide_ui()
        else:
            self.show_ui()

    def hide_ui(self):
        AppHelper.callAfter(self._hide_window_instance)

    def _hide_window_instance(self):
        if self.window:
            self.window.hide()
            self.is_visible = False

    def show_ui(self):
        AppHelper.callAfter(self._show_window_instance)

    def _show_window_instance(self):
        if self.window:
            self.window.show()
            self.is_visible = True


def main():
    controller = ColorGrabberController()
    html_content = read_html_ui()
    
    window = webview.create_window(
        title='Color Hub',
        html=html_content,
        width=780,
        height=680,
        x=2000,
        y=35,
        background_color='#121212',
        frameless=True,
        hidden=True,
        on_top=True,
        js_api=controller
    )
    
    controller.bind_window(window)
    

    def on_loaded():
        AppHelper.callAfter(controller.initialize_menu_bar)
        
        window.evaluate_js('''
            window.addEventListener('blur', () => {
                if (window.pywebview && window.pywebview.api) {
                    window.pywebview.api.hide_ui();
                }
            });
        ''')
        
    window.events.loaded += on_loaded
    webview.start()


def read_html_ui():
    html_path = resolve_resource_path("standalone.html")
    with open(html_path, 'r', encoding='utf-8') as file:
        return file.read()


def resolve_resource_path(file_name):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, file_name)


if __name__ == '__main__':
    main()
