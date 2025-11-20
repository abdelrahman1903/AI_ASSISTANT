import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:just_audio/just_audio.dart'; // optional: for TTS playback later

void main() {
  runApp(const MyApp());
}

const String token =
    "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MGU0MDVkNTgxMmJkNzkyZTMwNmMzYSIsImlhdCI6MTc2MjY0NzAyNCwiZXhwIjoxNzcwNDIzMDI0fQ.ndosHzgOnE7-raryIH_oAkKF_77p9xoNVBcKynbqgXw";
const String backendUrl =
    'http://127.0.0.1:8000/chat'; // <-- change this if using emulator or remote server

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Assistant Prototype',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, dynamic>> _messages =
      []; // {'sender': 'user'|'assistant', 'text': '...'}
  bool _isLoading = false;
  bool _isRecording = false;
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer(); // optional for TTS playback

  Future<void> _onMicPressed() async {
    if (_isRecording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    try {
      if (await _recorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final filePath = '${dir.path}/recording.webm';

        // Start recording in webm/opus format
        await _recorder.start(
          const RecordConfig(
            encoder: AudioEncoder.wav, // use m4a for iOS if needed
            bitRate: 128000,
            sampleRate: 44100,
          ),
          path: filePath,
        );

        setState(() => _isRecording = true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Microphone permission denied')),
        );
      }
    } catch (e) {
      print("🎤 Recording error: $e");
    }
  }

  Future<void> _stopRecording() async {
    try {
      final filePath = await _recorder.stop();
      setState(() => _isRecording = false);

      if (filePath != null) {
        await _uploadAudio(File(filePath));
      }
    } catch (e) {
      print("🛑 Stop recording error: $e");
    }
  }

  Future<void> _uploadAudio(File file) async {
    setState(() {
      _messages.add({'sender': 'user', 'text': '🎤 Sent voice message...'});
      _isLoading = true;
    });

    try {
      final uri = Uri.parse("http://127.0.0.1:8000/audio");
      final request = http.MultipartRequest("POST", uri);
      request.files.add(await http.MultipartFile.fromPath("audio", file.path));
      request.headers['Authorization'] = token;

      final streamedResponse = await request.send();
      final resp = await http.Response.fromStream(streamedResponse);

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body);
        final transcription =
            data["Transcription"] ?? "No transcription received.";
        setState(() {
          _messages.add({'sender': 'assistant', 'text': transcription});
        });
      } else {
        setState(() {
          _messages.add({
            'sender': 'assistant',
            'text': 'Upload failed: ${resp.statusCode}',
          });
        });
      }
    } catch (e) {
      setState(() {
        _messages.add({'sender': 'assistant', 'text': 'Error: $e'});
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _messages.add({'sender': 'user', 'text': text});
      _isLoading = true;
      _controller.clear();
    });

    try {
      final resp = await http.post(
        Uri.parse(backendUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token, // 👈 Add this line
        },
        body: jsonEncode({'text': text}),
      );

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body);
        final reply =
            data['response'] ?? data['message'] ?? 'No reply field in response';
        setState(() {
          _messages.add({'sender': 'assistant', 'text': reply});
        });

        // optional: if your backend returns a 'ttsUrl' you can play it:
        if (data['ttsUrl'] != null) {
          try {
            await _audioPlayer.setUrl(data['ttsUrl']);
            _audioPlayer.play();
          } catch (_) {}
        }
      } else {
        setState(() {
          _messages.add({
            'sender': 'assistant',
            'text': 'Server error: ${resp.statusCode} ${resp.reasonPhrase}',
          });
        });
      }
    } catch (e) {
      setState(() {
        _messages.add({'sender': 'assistant', 'text': 'Network error: $e'});
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Microphone button is a UI stub for now.
  // void _onMicPressed() {
  //   // Placeholder: later we'll replace this with recorder code or open the native recorder
  //   ScaffoldMessenger.of(context).showSnackBar(
  //     const SnackBar(content: Text('Mic pressed (not implemented yet)')),
  //   );
  // }

  @override
  void dispose() {
    _recorder.dispose();
    _controller.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  Widget _buildMessageTile(Map<String, dynamic> msg) {
    final bool isUser = msg['sender'] == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isUser ? Colors.blueAccent : Colors.grey[850],
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(isUser ? 16 : 4),
              bottomRight: Radius.circular(isUser ? 4 : 16),
            ),
          ),
          child: Text(msg['text'] ?? '', style: const TextStyle(fontSize: 16)),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Assistant Prototype'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_forever),
            tooltip: 'Clear chat',
            onPressed: () => setState(() => _messages.clear()),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.only(top: 12, bottom: 12),
              itemCount: _messages.length,
              itemBuilder: (context, i) => _buildMessageTile(_messages[i]),
            ),
          ),
          if (_isLoading) const LinearProgressIndicator(minHeight: 3),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  IconButton(
                    icon: Icon(
                      _isRecording ? Icons.stop : Icons.mic,
                      color: _isRecording ? Colors.redAccent : Colors.white,
                    ),
                    onPressed: _onMicPressed,
                    tooltip: _isRecording
                        ? 'Stop recording'
                        : 'Start recording',
                  ),
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _sendMessage(),
                      decoration: InputDecoration(
                        hintText: 'Type a message...',
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        isDense: true,
                        filled: true,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
