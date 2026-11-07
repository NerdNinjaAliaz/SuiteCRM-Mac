// SuiteCRM for Mac — small AppKit + WKWebView shell
// Build (on macOS): swiftc MacApp.swift -framework Cocoa -framework WebKit -o SuiteCRM-Mac
// No PHP / MySQL server is required for this standalone demo.
import AppKit
import Foundation
import WebKit
import UniformTypeIdentifiers

final class SuiteCRMMacApp: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!

    private var dataDirectory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("SuiteCRM-for-Mac", isDirectory: true)
    }
    private var dataFile: URL { dataDirectory.appendingPathComponent("beans.json") }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        let controller = WKUserContentController()
        controller.add(self, name: "crmBridge")

        if let saved = try? Data(contentsOf: dataFile) {
            let encoded = saved.base64EncodedString()
            let source = """
            (() => {
              try {
                const binary = atob('\(encoded)');
                const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
                window.__suitecrmNativeInitialData = JSON.parse(new TextDecoder().decode(bytes));
              } catch (error) { console.error('Unable to restore CRM database', error); }
            })();
            """
            controller.addUserScript(WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        // Native traffic-light buttons are supplied by NSWindow, not fake web controls.
        let chrome = """
        document.addEventListener('DOMContentLoaded', () => {
          const controls = document.querySelector('#btnTrafficClose')?.parentElement;
          if (controls) controls.style.display = 'none';
        });
        """
        controller.addUserScript(WKUserScript(source: chrome, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        config.userContentController = controller
        webView = WKWebView(frame: NSRect(x: 0, y: 0, width: 1250, height: 800), configuration: config)
        webView.navigationDelegate = self

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1250, height: 800),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false
        )
        window.title = "SuiteCRM for Mac"
        window.minSize = NSSize(width: 830, height: 560)
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        installMenu()

        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)
        let executableDir = URL(fileURLWithPath: CommandLine.arguments[0]).standardizedFileURL.deletingLastPathComponent()
        let candidates = [
            cwd.appendingPathComponent("suitecrm_mac.html"),
            executableDir.appendingPathComponent("suitecrm_mac.html"),
            executableDir.appendingPathComponent("../Resources/suitecrm_mac.html").standardizedFileURL
        ]
        guard let htmlFile = candidates.first(where: { FileManager.default.fileExists(atPath: $0.path) }) else {
            let alert = NSAlert()
            alert.messageText = "Cannot find suitecrm_mac.html"
            alert.informativeText = "Keep the HTML file beside SuiteCRM-Mac, or launch from the mac-desktop directory."
            alert.runModal()
            NSApp.terminate(nil)
            return
        }
        webView.loadFileURL(htmlFile, allowingReadAccessTo: htmlFile.deletingLastPathComponent())
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    private func installMenu() {
        let bar = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Quit SuiteCRM for Mac", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        bar.addItem(appItem)
        let editItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Find Customer / Deal", action: #selector(focusSearch(_:)), keyEquivalent: "k")
        editMenu.addItem(.separator())
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editItem.submenu = editMenu
        bar.addItem(editItem)
        NSApp.mainMenu = bar
    }

    @objc private func focusSearch(_ sender: Any?) {
        webView.evaluateJavaScript("document.getElementById('globalSearchInput')?.focus();")
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "crmBridge", let payload = message.body as? [String: Any],
              let action = payload["action"] as? String,
              let content = payload["data"] as? String else { return }
        guard content.utf8.count <= 30_000_000 else { return } // avoid oversized WebKit messages
        if action == "save" {
            // Ensure only JSON objects are saved. Do not let arbitrary JS choose file paths.
            guard (try? JSONSerialization.jsonObject(with: Data(content.utf8))) is [String: Any] else { return }
            do {
                try FileManager.default.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
                try Data(content.utf8).write(to: dataFile, options: .atomic)
            } catch { NSLog("SuiteCRM save failed: %@", String(describing: error)) }
        } else if action == "export" {
            guard (try? JSONSerialization.jsonObject(with: Data(content.utf8))) is [String: Any] else { return }
            let dialog = NSSavePanel()
            dialog.nameFieldStringValue = "suitecrm_mac_beans_export.json"
            dialog.allowedContentTypes = [.json]
            if dialog.runModal() == .OK, let url = dialog.url {
                do { try content.write(to: url, atomically: true, encoding: .utf8) }
                catch { NSLog("SuiteCRM export failed: %@", String(describing: error)) }
            }
        }
    }

    // External links open in the default browser, not in the trusted local CRM origin.
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if url.isFileURL || url.scheme == "about" {
            decisionHandler(.allow)
        } else {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
        }
    }
}

let application = NSApplication.shared
application.setActivationPolicy(.regular)
let delegate = SuiteCRMMacApp()
application.delegate = delegate
application.run()
