import Foundation
import Vision
import ImageIO

let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hant", "en-US"]
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(url: url, options: [:])
try handler.perform([request])
let lines: [[String: Any]] = (request.results ?? []).compactMap { observation in
    guard let text = observation.topCandidates(1).first else { return nil }
    return ["text": text.string, "confidence": Double(text.confidence) * 100,
            "box": [observation.boundingBox.minX, observation.boundingBox.minY,
                    observation.boundingBox.width, observation.boundingBox.height]]
}
let payload: [String: Any] = ["engine": "apple-vision", "lines": lines]
let output = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
print(String(data: output, encoding: .utf8)!)
