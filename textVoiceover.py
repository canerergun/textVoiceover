import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import tempfile
import pygame
import threading
import asyncio
from datetime import datetime

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class ModernTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seslendirme")
        self.root.geometry("1100x700")
        self.root.minsize(850, 550)

        # ── Renkler ──
        self.BG       = "#f5f7fb"
        self.CARD     = "#ffffff"
        self.PRIMARY  = "#4361ee"
        self.SUCCESS  = "#2ecc71"
        self.DANGER   = "#e74c3c"
        self.ACCENT   = "#7c3aed"
        self.TEXT      = "#1e293b"
        self.SUBTEXT   = "#64748b"
        self.BORDER    = "#e2e8f0"

        self.root.configure(bg=self.BG)

        # ── Değişkenler ──
        self.audio_file_path = None
        self.generated_audio_path = None
        self.is_playing = False

        # Pygame
        pygame.mixer.init()

        # Tek ses: Emel
        self.voice_id = "tr-TR-EmelNeural"

        # ── Grid ──
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_content()
        self._build_footer()

        if not EDGE_TTS_AVAILABLE:
            messagebox.showwarning(
                "Eksik Kütüphane",
                "edge-tts kurulu değil.\n\npip install edge-tts"
            )

    # ────────────────────── HEADER ──────────────────────
    def _build_header(self):
        header = tk.Frame(self.root, bg=self.CARD, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # Logo
        tk.Label(
            header, text="🎙️", font=("Segoe UI Emoji", 28),
            bg=self.CARD
        ).grid(row=0, column=0, padx=(25, 8), pady=15)

        # Başlık
        title_box = tk.Frame(header, bg=self.CARD)
        title_box.grid(row=0, column=1, sticky="w")

        tk.Label(
            title_box, text="Seslendirme", font=("Segoe UI", 18, "bold"),
            bg=self.CARD, fg=self.TEXT
        ).pack(anchor="w")

        tk.Label(
            title_box, text="Emel · Türkçe Yapay Zeka Sesi",
            font=("Segoe UI", 10), bg=self.CARD, fg=self.SUBTEXT
        ).pack(anchor="w")

        # Karakter sayacı
        self.char_label = tk.Label(
            header, text="0 karakter", font=("Segoe UI", 10),
            bg=self.CARD, fg=self.SUBTEXT
        )
        self.char_label.grid(row=0, column=2, padx=25)

        # Alt çizgi
        tk.Frame(
            self.root, bg=self.BORDER, height=1
        ).grid(row=0, column=0, sticky="sew")

    # ────────────────────── CONTENT ──────────────────────
    def _build_content(self):
        content = tk.Frame(self.root, bg=self.BG)
        content.grid(row=1, column=0, sticky="nsew", padx=25, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)
        content.grid_rowconfigure(0, weight=1)

        # ── Sol: Metin alanı ──
        left = tk.Frame(content, bg=self.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Üst bar
        bar = tk.Frame(left, bg=self.BG)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        tk.Label(
            bar, text="Metin", font=("Segoe UI", 12, "bold"),
            bg=self.BG, fg=self.TEXT
        ).pack(side=tk.LEFT)

        # Küçük butonlar
        for icon, cmd, tip in [
            ("📂", self.open_file, "Dosya Aç"),
            ("📋", self.add_example, "Örnek"),
            ("✕", self.clear_text, "Temizle"),
        ]:
            b = tk.Button(
                bar, text=icon, font=("Segoe UI Emoji", 11),
                bg=self.BG, fg=self.SUBTEXT, bd=0, cursor="hand2",
                activebackground=self.BG, command=cmd
            )
            b.pack(side=tk.RIGHT, padx=3)

        # Metin kutusu
        text_card = tk.Frame(left, bg=self.CARD, highlightbackground=self.BORDER,
                             highlightthickness=1, bd=0)
        text_card.grid(row=1, column=0, sticky="nsew")
        text_card.grid_rowconfigure(0, weight=1)
        text_card.grid_columnconfigure(0, weight=1)

        self.text_input = tk.Text(
            text_card, wrap=tk.WORD, font=("Segoe UI", 12),
            bg=self.CARD, fg=self.TEXT, insertbackground=self.PRIMARY,
            selectbackground=self.PRIMARY, selectforeground="#ffffff",
            relief=tk.FLAT, padx=18, pady=14, undo=True,
            spacing1=2, spacing3=2
        )
        self.text_input.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(text_card, orient=tk.VERTICAL,
                                  command=self.text_input.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_input.configure(yscrollcommand=scrollbar.set)
        self.text_input.bind("<KeyRelease>", self._update_counter)

        # ── Sağ: Kontrol paneli ──
        right = tk.Frame(content, bg=self.CARD, width=260,
                         highlightbackground=self.BORDER,
                         highlightthickness=1, bd=0)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)

        self._build_controls(right)

    def _build_controls(self, parent):
        pad = 18

        # ── Hız ──
        tk.Label(
            parent, text="Okuma Hızı", font=("Segoe UI", 11, "bold"),
            bg=self.CARD, fg=self.TEXT
        ).pack(anchor="w", padx=pad, pady=(pad, 4))

        speed_frame = tk.Frame(parent, bg=self.CARD)
        speed_frame.pack(fill=tk.X, padx=pad)

        self.speed_var = tk.IntVar(value=100)
        self.speed_label = tk.Label(
            speed_frame, text="100%", font=("Segoe UI", 10, "bold"),
            bg=self.CARD, fg=self.PRIMARY, width=5
        )
        self.speed_label.pack(side=tk.RIGHT)

        scale_style = ttk.Style()
        scale_style.configure(
            "Custom.Horizontal.TScale",
            troughcolor=self.BORDER,
            background=self.PRIMARY,
        )

        self.speed_scale = ttk.Scale(
            speed_frame, from_=50, to=200,
            variable=self.speed_var, orient=tk.HORIZONTAL,
            command=self._on_speed_change,
            style="Custom.Horizontal.TScale"
        )
        self.speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        # Hız kısayolları
        preset_frame = tk.Frame(parent, bg=self.CARD)
        preset_frame.pack(fill=tk.X, padx=pad, pady=(4, 0))

        for label, value in [("Yavaş", 75), ("Normal", 100), ("Hızlı", 140)]:
            b = tk.Button(
                preset_frame, text=label, font=("Segoe UI", 8),
                bg=self.BG, fg=self.SUBTEXT, bd=0, cursor="hand2",
                activebackground=self.BORDER, padx=8, pady=2,
                command=lambda v=value: self._set_speed(v)
            )
            b.pack(side=tk.LEFT, padx=(0, 4))

        # ── Ayırıcı ──
        tk.Frame(parent, bg=self.BORDER, height=1).pack(
            fill=tk.X, padx=pad, pady=16
        )

        # ── Ana butonlar ──
        tk.Label(
            parent, text="İşlemler", font=("Segoe UI", 11, "bold"),
            bg=self.CARD, fg=self.TEXT
        ).pack(anchor="w", padx=pad, pady=(0, 8))

        buttons = [
            ("🔊  Seslendir", self.PRIMARY, self.speak_text),
            ("💾  Kaydet", self.ACCENT, self.save_audio_direct),
        ]

        for text, color, cmd in buttons:
            self._make_button(parent, text, color, cmd, pad)

        # ── Oynatma kontrolleri ──
        tk.Frame(parent, bg=self.BORDER, height=1).pack(
            fill=tk.X, padx=pad, pady=16
        )

        play_frame = tk.Frame(parent, bg=self.CARD)
        play_frame.pack(fill=tk.X, padx=pad)
        play_frame.grid_columnconfigure(0, weight=1)
        play_frame.grid_columnconfigure(1, weight=1)

        self.play_btn = tk.Button(
            play_frame, text="▶  Dinle", font=("Segoe UI", 10),
            bg=self.SUCCESS, fg="white", bd=0, cursor="hand2",
            activebackground="#27ae60", pady=8, relief=tk.FLAT,
            command=self.play_audio
        )
        self.play_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.stop_btn = tk.Button(
            play_frame, text="■  Dur", font=("Segoe UI", 10),
            bg=self.DANGER, fg="white", bd=0, cursor="hand2",
            activebackground="#c0392b", pady=8, relief=tk.FLAT,
            command=self.stop_audio
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # ── Alt bilgi ──
        spacer = tk.Frame(parent, bg=self.CARD)
        spacer.pack(fill=tk.BOTH, expand=True)

        info = tk.Label(
            parent, text="Emel Neural · Microsoft Edge TTS",
            font=("Segoe UI", 8), bg=self.CARD, fg="#94a3b8"
        )
        info.pack(side=tk.BOTTOM, pady=pad)

    def _make_button(self, parent, text, color, command, pad):
        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 11, "bold"),
            bg=color, fg="white", bd=0, cursor="hand2",
            activebackground=color, pady=10, relief=tk.FLAT,
            command=command
        )
        btn.pack(fill=tk.X, padx=pad, pady=(0, 6))

        # Hover efekti
        def on_enter(e, b=btn, c=color):
            b.configure(bg=self._lighten(c))

        def on_leave(e, b=btn, c=color):
            b.configure(bg=c)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    @staticmethod
    def _lighten(hex_color, factor=0.15):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ────────────────────── FOOTER ──────────────────────
    def _build_footer(self):
        footer = tk.Frame(self.root, bg=self.CARD, height=36)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        tk.Frame(self.root, bg=self.BORDER, height=1).grid(
            row=2, column=0, sticky="new"
        )

        self.status_var = tk.StringVar(value="Hazır")
        tk.Label(
            footer, textvariable=self.status_var,
            font=("Segoe UI", 9), bg=self.CARD, fg=self.SUBTEXT
        ).grid(row=0, column=0, sticky="w", padx=25, pady=8)

        self.progress = ttk.Progressbar(footer, mode='indeterminate', length=160)
        self.progress.grid(row=0, column=1, padx=25, pady=8)

    # ────────────────────── İŞLEVLER ──────────────────────
    def _update_counter(self, event=None):
        text = self.text_input.get("1.0", tk.END).strip()
        n = len(text)
        w = len(text.split()) if text else 0
        self.char_label.config(text=f"{n} karakter · {w} kelime")

    def _on_speed_change(self, val):
        v = int(float(val))
        self.speed_label.config(text=f"{v}%")

    def _set_speed(self, value):
        self.speed_var.set(value)
        self.speed_label.config(text=f"{value}%")

    def _get_rate(self):
        s = self.speed_var.get()
        diff = s - 100
        return f"+{diff}%" if diff >= 0 else f"{diff}%"

    # ── Seslendirme ──
    def speak_text(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Uyarı", "Lütfen metin girin.")
            return
        if not EDGE_TTS_AVAILABLE:
            messagebox.showerror("Hata", "edge-tts kurulu değil!")
            return

        self.progress.start()
        self.status_var.set("Ses oluşturuluyor…")

        t = threading.Thread(
            target=self._generate_audio,
            args=(text, self._get_rate(), self._on_play_ready),
            daemon=True
        )
        t.start()

    def _generate_audio(self, text, rate, callback):
        async def _run():
            comm = edge_tts.Communicate(text=text, voice=self.voice_id, rate=rate)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                path = f.name
            await comm.save(path)
            return path

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            path = loop.run_until_complete(_run())
            self.root.after(0, lambda: callback(path, None))
        except Exception as e:
            self.root.after(0, lambda: callback(None, str(e)))
        finally:
            loop.close()

    def _on_play_ready(self, path, error):
        self.progress.stop()
        if error:
            messagebox.showerror("Hata", error)
            self.status_var.set("Hata oluştu")
            return
        self.audio_file_path = path
        self._play_file(path)

    def _play_file(self, path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.status_var.set("Dinleniyor…")
            self._check_playback()
        except Exception as e:
            messagebox.showerror("Hata", f"Oynatılamadı: {e}")

    def _check_playback(self):
        if pygame.mixer.music.get_busy():
            self.root.after(100, self._check_playback)
        else:
            self.is_playing = False
            self.status_var.set("Hazır")
            self._cleanup_temp(self.audio_file_path)
            self.audio_file_path = None

    def play_audio(self):
        if self.generated_audio_path and os.path.exists(self.generated_audio_path):
            self._play_file(self.generated_audio_path)
        else:
            messagebox.showinfo("Bilgi", "Önce seslendirin veya kaydedin.")

    def stop_audio(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self.is_playing = False
            self.status_var.set("Durduruldu")

    # ── Kaydetme ──
    def save_audio_direct(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Uyarı", "Lütfen metin girin.")
            return
        if not EDGE_TTS_AVAILABLE:
            messagebox.showerror("Hata", "edge-tts kurulu değil!")
            return

        self.progress.start()
        self.status_var.set("Dosya oluşturuluyor…")

        t = threading.Thread(
            target=self._generate_audio,
            args=(text, self._get_rate(), self._on_save_ready),
            daemon=True
        )
        t.start()

    def _on_save_ready(self, path, error):
        self.progress.stop()
        if error:
            messagebox.showerror("Hata", error)
            self.status_var.set("Hata oluştu")
            return

        self.generated_audio_path = path
        default = f"ses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("Tümü", "*.*")],
            initialfile=default,
            title="Kaydet"
        )

        if save_path:
            try:
                import shutil
                shutil.copy2(path, save_path)
                self.status_var.set(f"Kaydedildi: {os.path.basename(save_path)}")
                messagebox.showinfo("Başarılı", f"Kaydedildi:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Hata", str(e))
        else:
            self.status_var.set("Hazır")

        self._cleanup_temp(path)

    # ── Yardımcılar ──
    @staticmethod
    def _cleanup_temp(path):
        if path and os.path.exists(path):
            try:
                pygame.mixer.music.unload()
            except:
                pass
            try:
                os.remove(path)
            except:
                pass

    def clear_text(self):
        self.text_input.delete("1.0", tk.END)
        self._update_counter()
        self.status_var.set("Temizlendi")

    def add_example(self):
        example = (
            "Merhaba! Bu modern seslendirme uygulamasına hoş geldiniz.\n\n"
            "Yapay zeka destekli Emel sesi ile metinlerinizi doğal bir şekilde "
            "seslendirebilirsiniz. Okuma hızını ayarlayabilir, sesi dinleyebilir "
            "veya MP3 olarak kaydedebilirsiniz.\n\n"
            "Türkçe karakterler ve noktalama işaretleri sorunsuz çalışır. "
            "Keyifli kullanımlar!"
        )
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", example)
        self._update_counter()
        self.status_var.set("Örnek metin eklendi")

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Metin", "*.txt"), ("Tümü", "*.*")],
            title="Dosya Aç"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.text_input.delete("1.0", tk.END)
                    self.text_input.insert("1.0", f.read())
                self._update_counter()
                self.status_var.set(f"Açıldı: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Hata", str(e))


def main():
    root = tk.Tk()

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TProgressbar", troughcolor="#e2e8f0", background="#4361ee")

    app = ModernTTSApp(root)

    # Ortala
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

    def on_close():
        try:
            pygame.mixer.quit()
        except:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()