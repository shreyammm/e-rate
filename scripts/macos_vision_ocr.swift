// Apple Vision OCR helper for locally rendered document page PNGs.
// No network access; stdout is structured JSON for per-page evidence.
import Foundation
import Vision

struct Line: Encodable {
    let text: String
    let confidence: Float
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}
struct Output: Encodable { let lines: [Line] }

if CommandLine.arguments.count != 2 {
    fputs("usage: macos_vision_ocr IMAGE.png\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
if #available(macOS 13.0, *) {
    request.automaticallyDetectsLanguage = true
}
do {
    let handler = VNImageRequestHandler(url: url, options: [:])
    try handler.perform([request])
    let observations = (request.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.012 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }
    let lines: [Line] = observations.compactMap { item in
        guard let candidate = item.topCandidates(1).first else { return nil }
        let b = item.boundingBox
        return Line(text: candidate.string, confidence: candidate.confidence,
                    x: b.minX, y: b.minY, width: b.width, height: b.height)
    }
    let output = try JSONEncoder().encode(Output(lines: lines))
    guard let s = String(data: output, encoding: .utf8) else { throw NSError(domain: "UTF8", code: 1) }
    print(s)
} catch {
    fputs("Vision OCR failed: \(error)\n", stderr)
    exit(1)
}
