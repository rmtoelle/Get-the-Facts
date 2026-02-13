import SwiftUI

struct ContentView: View {
    @State private var claimText: String = ""
    @State private var statusMessages: [String] = []
    @State private var finalVerdict: String = ""
    @State private var sources: [String] = []
    @State private var isAnalyzing: Bool = false
    
    var body: some View {
        ZStack {
            // Background Gradient
            LinearGradient(gradient: Gradient(colors: [Color.black, Color(red: 0.1, green: 0.1, blue: 0.2)]), startPoint: .top, endPoint: .bottom)
                .edgesIgnoringSafeArea(.all)
            
            VStack(spacing: 20) {
                // Header
                Text("GET THE FACTS")
                    .font(.system(size: 28, weight: .black, design: .monospaced))
                    .foregroundColor(.cyan)
                    .padding(.top, 40)
                
                // Input Field
                TextField("Enter claim to verify...", text: $claimText)
                    .padding()
                    .background(Color.white.opacity(0.1))
                    .cornerRadius(12)
                    .foregroundColor(.white)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.cyan.opacity(0.5), lineWidth: 1))
                    .padding(.horizontal)
                
                // Verify Button
                Button(action: startVerification) {
                    Text(isAnalyzing ? "ANALYZING..." : "VERIFY WITH QUANTUM BRAIN")
                        .font(.headline)
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(isAnalyzing ? Color.gray : Color.cyan)
                        .cornerRadius(12)
                }
                .disabled(isAnalyzing || claimText.isEmpty)
                .padding(.horizontal)
                
                // Engine "Racing Tree" Status
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(statusMessages, id: \.self) { msg in
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                            Text(msg)
                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                .foregroundColor(.white.opacity(0.8))
                        }
                        .transition(.move(edge: .leading))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal)
                
                // Results Area
                if !finalVerdict.isEmpty {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 15) {
                            Text("CROSS-VERIFIED SUMMARY")
                                .font(.caption)
                                .foregroundColor(.cyan)
                                .bold()
                            
                            Text(finalVerdict)
                                .foregroundColor(.white)
                                .font(.body)
                                .padding()
                                .background(Color.white.opacity(0.05))
                                .cornerRadius(10)
                            
                            Text("EVIDENCE SOURCES")
                                .font(.caption)
                                .foregroundColor(.cyan)
                                .bold()
                            
                            ForEach(sources, id: \.self) { source in
                                Link(destination: URL(string: source)!) {
                                    HStack {
                                        Image(systemName: "link.circle.fill")
                                        Text(source)
                                            .lineLimit(1)
                                            .font(.caption)
                                    }
                                    .padding(8)
                                    .background(Color.blue.opacity(0.2))
                                    .cornerRadius(8)
                                }
                            }
                        }
                        .padding()
                    }
                }
                
                Spacer()
            }
        }
    }
    
    func startVerification() {
        isAnalyzing = true
        statusMessages = []
        finalVerdict = ""
        sources = []
        
        // This is where you point to your Render URL
        let url = URL(string: "https://YOUR-RENDER-APP-NAME.onrender.com/verify")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["text": claimText]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        // Streaming logic and update handling would go here...
        // For testing, we simulate the status messages:
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            statusMessages.append("GROK ENGINE: LOCKED")
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                statusMessages.append("GEMINI ENGINE: LOCKED")
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                    statusMessages.append("OPENAI ENGINE: LOCKED")
                    // Real implementation calls the API here
                }
            }
        }
    }
}
