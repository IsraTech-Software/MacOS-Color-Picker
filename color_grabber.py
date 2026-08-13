#!/usr/bin/env python3
import os
import sys
import threading
import objc
import webview
from AppKit import (
    NSStatusBar, 
    NSVariableStatusItemLength, 
    NSImage, 
    NSSize, 
    NSCalibratedRGBColorSpace, 
    NSColorSampler
)
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
        self.is_picking = False
        self.delegate = None
        self.status_bar = None
        self.status_item = None
        self._sampler = None  
        self._selection_block = None

    def bind_window(self, window):
        self.window = window

    def initialize_menu_bar(self):
        self.delegate = StatusBarDelegate.alloc().init()
        self.delegate.controller = self

        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        
        button = self.status_item.button()
        icon_path = resolve_resource_path(os.path.join(".", "icon.png"))
        
        if os.path.exists(icon_path):
            icon_image = NSImage.alloc().initWithContentsOfFile_(icon_path)
            icon_image.setSize_(NSSize(18, 18))
            icon_image.setTemplate_(False)
            button.setImage_(icon_image)
        else:
            button.setTitle_("🎨")

        button.setTarget_(self.delegate)
        button.setAction_(objc.selector(self.delegate.onIconClick_, signature=b'v@:@'))

    def pick_screen_color(self):
        self.is_picking = True
        # Do NOT hide the UI; force the window to stay open to prevent bridge collapse
        AppHelper.callAfter(self._launch_native_sampler)

    def _launch_native_sampler(self):
        self._sampler = NSColorSampler.alloc().init()

        def selection_handler(color):
            if color:
                try:
                    rgb_color = color.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
                    if rgb_color:
                        r = int(rgb_color.redComponent() * 255)
                        g = int(rgb_color.greenComponent() * 255)
                        b = int(rgb_color.blueComponent() * 255)
                        
                        # THE FIX: Offload JS evaluation to a detached background thread 
                        # so the Cocoa main thread can finish tearing down the native modal without deadlocking.
                        threading.Timer(0.1, self._dispatch_to_js, args=(r, g, b)).start()
                        return
                except Exception as e:
                    print(f"Color conversion failed: {e}")
            
            self.is_picking = False
            self._cleanup_sampler()

        self._selection_block = selection_handler
        self._sampler.showSamplerWithSelectionHandler_(self._selection_block)

    def _dispatch_to_js(self, r, g, b):
        if self.window:
            self.window.evaluate_js(f"updateColor({r}, {g}, {b});")
        self.is_picking = False
        self._cleanup_sampler()

    def _cleanup_sampler(self):
        self._sampler = None
        self._selection_block = None

    def toggle_visibility(self):
        if self.is_visible:
            self.hide_ui()
        else:
            self.show_ui()

    def hide_ui(self, force=False):
        # Crucial: Prevent the JS 'blur' event from destroying the window while picking
        if self.is_picking and not force:
            return
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
