import piexif
import os
import subprocess
import random
from datetime import datetime
from typing import Dict
from PIL import Image

class MediaSpoofer:
    def __init__(self):
        # Különböző eszköz profilok
        self.profiles = {
            "iphone_12_pro_max": {
                "Make": "Apple",
                "Model": "iPhone 12 Pro Max",
                "Software": "16.4.1",
                "LensModel": "iPhone 12 Pro Max back triple camera 5.1mm f/1.6"
            },
            "iphone_14_pro": {
                "Make": "Apple",
                "Model": "iPhone 14 Pro",
                "Software": "17.2",
                "LensModel": "iPhone 14 Pro back triple camera 6.86mm f/1.78"
            },
            "samsung_s23_ultra": {
                "Make": "Samsung",
                "Model": "SM-S918B",  # S23 Ultra kódja
                "Software": "S918BXXU1AWBD",
                "LensModel": ""
            },
            # Mivel az S25 még nincs, "kamuzunk" egy hihető kódot (S24=S928, tehát S25=S938)
            "samsung_s25_ultra_future": {
                "Make": "Samsung",
                "Model": "SM-S938B",
                "Software": "Android 15; One UI 7.0",
                "LensModel": ""
            },
            "samsung_a54": {
                "Make": "Samsung",
                "Model": "SM-A546B",
                "Software": "Android 14",
                "LensModel": ""
            }
        }

    def spoof_photo(self, image_path: str, device_key: str = "random") -> bool:
        """
        Fotó EXIF adatainak módosítása.
        """
        if not os.path.exists(image_path):
            print(f"❌ Fájl nem található: {image_path}")
            return False

        # Profil választás
        if device_key == "random" or device_key not in self.profiles:
            device_key = random.choice(list(self.profiles.keys()))

        profile = self.profiles[device_key]
        print(f"📸 Spoofing photo as {profile['Model']}...")

        try:
            # Check if file is PNG and convert to JPEG if needed
            img = Image.open(image_path)
            if img.format == 'PNG':
                print(f"🔄 Converting PNG to JPEG for EXIF support...")
                # Convert to RGB (PNG can have alpha channel)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Save as JPEG (overwrite original)
                img.save(image_path, 'JPEG', quality=95)
                print(f"✅ Converted to JPEG")

            # Meglévő EXIF betöltése vagy új létrehozása
            try:
                exif_dict = piexif.load(image_path)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            # 0th IFD (Fő adatok)
            exif_dict["0th"][piexif.ImageIFD.Make] = profile["Make"]
            exif_dict["0th"][piexif.ImageIFD.Model] = profile["Model"]
            exif_dict["0th"][piexif.ImageIFD.Software] = profile["Software"]
            
            # DateTime (Mostani idő, megfelelő formátumban)
            current_time = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
            exif_dict["0th"][piexif.ImageIFD.DateTime] = current_time
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = current_time
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = current_time

            # Lens Info (Ha van)
            if profile.get("LensModel"):
                exif_dict["Exif"][piexif.ExifIFD.LensModel] = profile["LensModel"]

            # Visszaírás a fájlba
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            
            return True

        except Exception as e:
            print(f"❌ Hiba a fotó spoofolása közben: {e}")
            return False

    def spoof_video(self, video_path: str, output_path: str = None, device_key: str = "random") -> bool:
        """
        Videó metadata módosítása ffmpeg segítségével.
        Ha nincs output_path, felülírja az eredetit (temp fájllal).
        """
        if not os.path.exists(video_path):
            return False

        if device_key == "random":
            device_key = random.choice(list(self.profiles.keys()))
        
        profile = self.profiles[device_key]
        print(f"🎥 Spoofing video as {profile['Model']}...")

        # Ha felülírást kérünk, kell egy temp fájl
        temp_output = output_path if output_path else f"{video_path}_temp.mp4"

        # FFMPEG parancs összeállítása
        # -map_metadata 0: megtartja az eredetit
        # -metadata key=value: felülírja a specifikusokat
        # -c copy: NEM kódolja újra a videót (nagyon gyors, minőségromlás mentes)
        
        creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        command = [
            "ffmpeg", "-y", # Overwrite output without asking
            "-i", video_path,
            "-c", "copy",   # Copy stream (no re-encoding)
            "-metadata", f"title=", # Törölje a címet ha volt
            "-metadata", f"artist=",
            "-metadata", f"creation_time={creation_time}",
            "-metadata", f"make={profile['Make']}",
            "-metadata", f"model={profile['Model']}",
            # Android specifikus metadata
            "-metadata", f"com.android.manufacturer={profile['Make']}",
            "-metadata", f"com.android.model={profile['Model']}",
            # Apple specifikus metadata (néha máshogy tárolják, de a 'make' általában elég)
            temp_output
        ]

        try:
            # Futtatás elrejtett kimenettel
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Ha felülírás volt a cél
            if not output_path:
                os.replace(temp_output, video_path)
            
            return True

        except subprocess.CalledProcessError:
            print("❌ Hiba: Az FFMPEG nem futott le. Telepítve van?")
            return False
        except Exception as e:
            print(f"❌ Hiba a videó spoofolása közben: {e}")
            return False

# Teszteléshez (ha önmagában futtatod)
if __name__ == "__main__":
    spoofer = MediaSpoofer()
    
    # Kép teszt (feltételezve, hogy van egy test.jpg)
    # spoofer.spoof_photo("test.jpg", "iphone_12_pro_max")
    
    # Videó teszt
    # spoofer.spoof_video("test.mp4", device_key="samsung_s25_ultra_future")
