import re
import os
import shutil
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

# Ayarlar
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
OUTPUT_FOLDER = "selcuk"
ALL_CHANNELS_FILE = "tum_kanallar.m3u" # Tüm kanalların toplanacağı dosya adı

def find_active_domain(start=1825, end=1950): # Aralığı biraz genişlettim
    """Aktif yayın domainini tarayarak bulur."""
    print(f"🔍 {start}-{end} aralığında aktif domain aranıyor...")
    for i in range(start, end + 1):
        url = f"https://www.selcuksportshd{i}.xyz/"
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=3) as response:
                html = response.read().decode('utf-8')
                if "uxsyplayer" in html or "m3u8" in html:
                    print(f"✅ Aktif domain bulundu: {url}")
                    return url, html
        except:
            continue
    return None, None

def slugify(name):
    """Dosya isimlerini Türkçe karakterlerden arındırır ve düzenler."""
    rep = {'ç':'c','Ç':'C','ş':'s','Ş':'S','ı':'i','İ':'I','ğ':'g','Ğ':'G','ü':'u','Ü':'U','ö':'o','Ö':'O'}
    for k, v in rep.items():
        name = name.replace(k, v)
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name

def get_player_links(html):
    """Ana sayfadaki kanal linklerini ve isimlerini toplar."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", attrs={"data-url": True}):
        data_url = a["data-url"].strip()
        if data_url.startswith("/"):
            data_url = "https://" + data_url.lstrip("/")
        
        name = a.text.strip()
        if not name:
            name = data_url.split("id=")[-1] if "id=" in data_url else "Kanal"
        
        links.append({"url": data_url, "name": name})
    return links

def get_m3u8_url(player_url, referer):
    """Player sayfasından asıl m3u8 yayın linkini ayıklar."""
    try:
        req = Request(player_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": referer})
        with urlopen(req, timeout=7) as response:
            html = response.read().decode('utf-8')
        
        patterns = [
            r'this\.baseStreamUrl\s*=\s*"([^"]+)"',
            r"this\.baseStreamUrl\s*=\s*'([^']+)'",
            r'baseStreamUrl\s*:\s*"([^"]+)"',
            r"baseStreamUrl\s*:\s*'([^']+)'"
        ]
        
        base_url = None
        for p in patterns:
            m = re.search(p, html)
            if m:
                base_url = m.group(1)
                break
        
        if not base_url: return None
        
        m_id = re.search(r"id=([a-zA-Z0-9]+)", player_url)
        if not m_id: return None
        
        stream_id = m_id.group(1)
        if not base_url.endswith("/"): base_url += "/"
        
        return f"{base_url}{stream_id}/playlist.m3u8"
    except:
        return None

def create_files():
    """Ana akış: Klasörü temizler, tekil ve toplu m3u dosyalarını oluşturur."""
    domain, html = find_active_domain()
    if not html:
        print("❌ Çalışan domain bulunamadı!")
        return

    # Klasör hazırlığı
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER)

    players = get_player_links(html)
    if not players:
        print("⚠️ Hiç kanal linki bulunamadı.")
        return

    print(f"📺 {len(players)} kanal işleniyor...\n")
    
    success_count = 0
    # Toplu liste içeriği için başlık
    master_m3u_content = ["#EXTM3U"]

    for ch in players:
        m3u8_link = get_m3u8_url(ch["url"], domain)
        if m3u8_link:
            # Tekil dosya içeriği
            single_content = [
                "#EXTM3U",
                f"#EXTINF:-1,{ch['name']}",
                f"#EXTVLCOPT:http-referrer={domain}",
                f"#EXTVLCOPT:http-user-agent={HEADERS['User-Agent']}",
                m3u8_link
            ]
            
            # Master listeye ekleme
            master_m3u_content.append(f"#EXTINF:-1,{ch['name']}")
            master_m3u_content.append(f"#EXTVLCOPT:http-referrer={domain}")
            master_m3u_content.append(f"#EXTVLCOPT:http-user-agent={HEADERS['User-Agent']}")
            master_m3u_content.append(m3u8_link)

            # Tekil dosyayı kaydet
            file_name = f"{slugify(ch['name'])}.m3u8"
            file_path = os.path.join(OUTPUT_FOLDER, file_name)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(single_content))
                success_count += 1
            except:
                pass
        else:
            print(f"❌ Link çekilemedi: {ch['name']}")

    # TÜM KANALLAR DOSYASINI KAYDET
    master_file_path = os.path.join(OUTPUT_FOLDER, ALL_CHANNELS_FILE)
    with open(master_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(master_m3u_content))

    print(f"\n🚀 İşlem Tamamlandı!")
    print(f"📂 Klasör: {OUTPUT_FOLDER}")
    print(f"📄 Ana Liste: {ALL_CHANNELS_FILE}")
    print(f"📊 Başarılı: {success_count} / {len(players)}")

if __name__ == "__main__":
    create_files()
