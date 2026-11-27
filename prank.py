import os, sys, time, ctypes
import tkinter as tk
import cv2, numpy as np
from PIL import Image, ImageTk
import pygame

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
VIDEO = os.path.join(BASE, "video.mp4")
AUDIO = os.path.join(BASE, "audio.wav")
SEUIL_NOIR = 40  # plus c'est haut, plus de noir est retiré


def volume_a_fond():
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        dev = AudioUtilities.GetSpeakers()
        itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = ctypes.cast(itf, ctypes.POINTER(IAudioEndpointVolume))
        vol.SetMute(0, None)
        vol.SetMasterVolumeLevelScalar(1.0, None)
    except Exception:
        # solution de secours : on appuie 60 fois sur "volume +"
        for _ in range(60):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)


def main():
    volume_a_fond()
    son = None
    for driver in (None, "directsound", "winmm"):
        try:
            if driver:
                os.environ["SDL_AUDIODRIVER"] = driver
                pygame.mixer.quit()
            pygame.mixer.init(44100)
            son = pygame.mixer.Sound(AUDIO)
            break
        except Exception:
            son = None  # pas de sortie audio : la vidéo tourne quand même

    root = tk.Tk()
    root.title("")
    W, H = root.winfo_screenwidth(), root.winfo_screenheight()
    root.configure(bg="black")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "black")  # le noir devient invisible
    root.config(cursor="none")
    canvas = tk.Canvas(root, width=W, height=H, bg="black", highlightthickness=0)
    canvas.pack()
    item = canvas.create_image(0, 0, anchor="nw")

    # Alt+F4 = seul moyen de quitter
    def quitter(*_):
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        root.destroy()
        os._exit(0)
    root.protocol("WM_DELETE_WINDOW", quitter)
    root.bind("<Alt-F4>", quitter)
    for k in ("<Escape>", "<Control-w>", "<Control-q>"):
        root.bind(k, lambda e: "break")

    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    etat = {"debut": time.time(), "img": None}
    if son:
        son.play()

    def boucle():
        t = time.time() - etat["debut"]
        cible = int(t * fps)
        pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        while pos < cible - 1:       # rattrapage si en retard
            if not cap.grab():
                break
            pos += 1
        ok, frame = cap.read()
        if not ok:                   # fin de la vidéo -> on recommence
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            etat["debut"] = time.time()
            if son:
                son.stop(); son.play()
            root.after(5, boucle)
            return
        frame = cv2.resize(frame, (W, H))
        masque = frame.max(axis=2) < SEUIL_NOIR
        frame = np.maximum(frame, 1)  # les pixels visibles ne sont jamais noir pur
        frame[masque] = 0             # fond = noir pur = transparent
        img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        etat["img"] = img
        canvas.itemconfig(item, image=img)
        root.after(1, boucle)

    def garder_devant():
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
        root.after(1000, garder_devant)

    boucle()
    garder_devant()
    root.mainloop()


if __name__ == "__main__":
    main()
