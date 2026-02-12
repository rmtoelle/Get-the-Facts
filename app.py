//
//  ContentView.swift
//  Get the Facts
//  Build 38 
//  Created by Robert M. Toelle on 2/11/26.
//  Copyright © 2026 Robert M. Toelle. All rights reserved.
//

import SwiftUI
import Combine
import StoreKit
import UIKit

// ==========================================
// 1. DATA MODELS
// ==========================================

struct VerificationResponse: Codable {
    let status: String
    let confidenceScore: Int
    let summary: String
    let sources: [String]
    let isSecure: Bool
}

struct ServerMessageRaw: Decodable {
    let type: String
    let data: [String: Any]
    enum CodingKeys: String, CodingKey { case type, data }
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        if let dict = try? container.decode([String: AnyDecodable].self, forKey: .data) {
            var temp = [String: Any]()
            for (k, v) in dict { temp[k] = v.value }
            data = temp
        } else { data = [:] }
    }
}

struct AnyDecodable: Decodable {
    let value: Any
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let x = try? container.decode(String.self) { value = x }
        else if let x = try? container.decode(Int.self) { value = x }
        else if let x = try? container.decode(Double.self) { value = x }
        else if let x = try? container.decode(Bool.self) { value = x }
        else if let x = try? container.decode([String].self) { value = x }
        else { value = "" }
    }
}

// ==========================================
// 2. HELPER COMPONENTS
// ==========================================

struct SelectableText: UIViewRepresentable {
    let text: String
    func makeUIView(context: Context) -> UITextView {
        let v = UITextView(); v.isEditable = false; v.isSelectable = true; v.backgroundColor = .clear; v.textColor = .label
        v.font = UIFont.systemFont(ofSize: 18); v.isScrollEnabled = true; v.textContainerInset = .zero
        return v
    }
    func updateUIView(_ uiView: UITextView, context: Context) { uiView.text = text }
}

struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: activityItems, applicationActivities: nil) }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

// ==========================================
// 3. MAIN CONTENT VIEW
// ==========================================
struct ContentView: View {
    let serverURL = "https://trifacts-brain.onrender.com/verify"
    
    @StateObject var storeManager = StoreKitManager()
    @State private var showPaywall = false
    @AppStorage("freeQueryCount") private var freeQueryCount = 0
    let freeLimit = 12
    
    @State private var inputText: String = ""
    @State private var isLoading: Bool = false
    @State private var result: VerificationResponse? = nil
    @State private var thinkingText: String = "Engines Ready"
    @State private var showShareSheet = false
    @State private var shareImage: UIImage? = nil
    
    var body: some View {
        ZStack {
            Color(uiColor: .systemGroupedBackground).edgesIgnoringSafeArea(.all)
            ScrollView {
                VStack(spacing: 12) {
                    // Header
                    VStack {
                        HStack {
                            Text("Get the Facts").font(.system(size: 34, weight: .bold, design: .rounded)).foregroundStyle(LinearGradient(colors: [.blue, .teal], startPoint: .leading, endPoint: .trailing))
                            Image(systemName: "shield.checkered").foregroundColor(.blue)
                        }
                        Text("Empirical Analysis System").font(.system(size: 10, weight: .black, design: .monospaced)).foregroundColor(.secondary)
                    }.padding(.top, 10)
                    
                    // Input
                    TextEditor(text: $inputText).frame(height: 120).padding(10).background(Color.white).cornerRadius(12).padding(.horizontal)
                    
                    // Action
                    Button(action: startVerification) {
                        Text(isLoading ? "RETRIEVING DATA..." : "VERIFY").font(.headline).frame(maxWidth: .infinity).padding().background(inputText.isEmpty ? Color.gray : Color.blue).foregroundColor(.white).clipShape(Capsule())
                    }.padding(.horizontal).disabled(isLoading || inputText.isEmpty)
                    
                    if let res = result {
                        VStack(spacing: 0) {
                            HStack {
                                Text(res.status).font(.title3).bold().foregroundColor(.green)
                                Spacer()
                                Button(action: takeScreenshot) {
                                    Label("X-SHOT", systemImage: "camera.fill").font(.caption).bold().padding(8).background(Color.black).foregroundColor(.white).clipShape(Capsule())
                                }
                            }.padding()
                            
                            Divider()
                            SelectableText(text: res.summary).frame(height: 100).padding()
                            
                            // CITATIONS SECTION
                            Divider()
                            VStack(alignment: .leading, spacing: 8) {
                                Text("VERIFIED SOURCES").font(.system(size: 10, weight: .black)).foregroundColor(.secondary)
                                ForEach(res.sources, id: \.self) { url in
                                    Link(destination: URL(string: url) ?? URL(string: "https://google.com")!) {
                                        HStack {
                                            Image(systemName: "link.circle.fill")
                                            Text(url).font(.system(size: 11)).lineLimit(1)
                                        }.padding(8).background(Color.blue.opacity(0.05)).cornerRadius(8)
                                    }
                                }
                            }.padding()
                        }.background(Color.white).cornerRadius(12).padding(.horizontal)
                    }
                }
            }
        }
        .sheet(isPresented: $showPaywall) { PaywallView(storeManager: storeManager) }
        .sheet(isPresented: $showShareSheet) { if let img = shareImage { ShareSheet(activityItems: [img]) } }
    }
    
    func startVerification() {
        isLoading = true; result = nil; thinkingText = "Fetching Citations..."
        guard let url = URL(string: serverURL) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"; request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["text": inputText])
        
        Task {
            do {
                let (bytes, _) = try await URLSession.shared.bytes(for: request)
                for try await line in bytes.lines {
                    if line.hasPrefix("data: ") {
                        let jsonStr = line.replacingOccurrences(of: "data: ", with: "")
                        if let data = jsonStr.data(using: .utf8), let msg = try? JSONDecoder().decode(ServerMessageRaw.self, from: data) {
                            await MainActor.run {
                                if msg.type == "result" {
                                    let s = msg.data["status"] as? String ?? "ANALYSIS"
                                    let sum = msg.data["summary"] as? String ?? ""
                                    let src = msg.data["sources"] as? [String] ?? []
                                    self.result = VerificationResponse(status: s, confidenceScore: 99, summary: sum, sources: src, isSecure: true)
                                    self.isLoading = false
                                }
                            }
                        }
                    }
                }
            } catch { await MainActor.run { isLoading = false } }
        }
    }

    func takeScreenshot() {
        let controller = UIHostingController(rootView: resultViewForScreenshot())
        let targetSize = CGSize(width: 375, height: 400)
        controller.view.bounds = CGRect(origin: .zero, size: targetSize)
        controller.view.backgroundColor = .white
        let renderer = UIGraphicsImageRenderer(size: targetSize)
        self.shareImage = renderer.image { _ in controller.view.drawHierarchy(in: controller.view.bounds, afterScreenUpdates: true) }
        self.showShareSheet = true
    }
    
    func resultViewForScreenshot() -> some View {
        VStack(alignment: .leading) {
            Text("GET THE FACTS").font(.caption).bold().foregroundColor(.blue)
            Text(result?.status ?? "").font(.title).bold()
            Divider()
            Text(result?.summary ?? "").font(.body)
        }.padding().frame(width: 375, height: 400).background(Color.white)
    }
}
