// Offscreen macOS application icon generator; no third-party dependencies.
import AppKit
import Foundation
let size = 1024
guard CommandLine.arguments.count == 2 else {
    fatalError("Usage: swift GenerateIcon.swift /path/to/icon.png")
}
guard let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
    isPlanar: false, colorSpaceName: .deviceRGB,
    bytesPerRow: 0, bitsPerPixel: 0
), let graphics = NSGraphicsContext(bitmapImageRep: bitmap) else {
    fatalError("Could not initialize offscreen icon graphics")
}
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = graphics
NSColor.clear.setFill()
NSRect(x: 0, y: 0, width: size, height: size).fill()
let tile = NSBezierPath(roundedRect: NSRect(x: 44, y: 44, width: 936, height: 936), xRadius: 218, yRadius: 218)
let darkBlue = NSColor(calibratedRed: 0.055, green: 0.105, blue: 0.24, alpha: 1)
let brightBlue = NSColor(calibratedRed: 0.12, green: 0.49, blue: 0.97, alpha: 1)
NSGradient(starting: brightBlue, ending: darkBlue)?.draw(in: tile, angle: -45)
let orbit = NSBezierPath(ovalIn: NSRect(x: 215, y: 220, width: 594, height: 594))
orbit.lineWidth = 20
NSColor(calibratedWhite: 1.0, alpha: 0.16).setStroke()
orbit.stroke()
let text = "S" as NSString
let font = NSFont.systemFont(ofSize: 610, weight: .bold)
let attributes: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: NSColor.white,
    .kern: -13
]
let dimensions = text.size(withAttributes: attributes)
text.draw(at: NSPoint(x: (CGFloat(size) - dimensions.width) / 2,
                      y: (CGFloat(size) - dimensions.height) / 2 - 20), withAttributes: attributes)
graphics.flushGraphics()
NSGraphicsContext.restoreGraphicsState()
guard let data = bitmap.representation(using: .png, properties: [:]) else {
    fatalError("Could not encode icon")
}
try data.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
