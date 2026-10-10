# GameNav

GameNav, Blender'ın 3D görünümünde oyunlardaki gibi rahatça hareket etmek için hazırlanmış bağımsız bir WASD gezinme eklentisidir. Özellikle büyük mimari sahnelerde, çevre tasarımlarında ve geniş ölçekli projelerde klasik orbit/pan/zoom kullanımını azaltır.

## Özellikler

- `W A S D` veya ok tuşlarıyla hareket
- Mouse ile serbest bakış
- `E / Q` ile yukarı ve aşağı hareket
- `Shift` ile hızlanma, `Alt` ile hassas/yavaş hareket
- Mouse tekerleğiyle oturum sırasında anlık hız ayarı
- Oda, Sahne ve Mega hız profilleri
- İsteğe bağlı yatay WASD hareketi
- Yumuşak hızlanma ve durma
- Seçili nesneye hızlı odaklanma
- Çok büyük sahneler için uzak görüş ayarı
- `.blend` dosyasına kaydedilen ana görünüm konumu
- Ayarlanabilir `Shift + F` kısayolu

## Kurulum

1. `gamenav-1.0.1.zip` dosyasını indir.
2. Blender'da **Edit > Preferences > Extensions** bölümünü aç.
3. Sağ üst menüden **Install from Disk** seçeneğine tıkla.
4. ZIP dosyasını seç ve GameNav'i etkinleştir.
5. 3D Viewport'ta `N` tuşuyla Sidebar'ı açıp **GameNav** sekmesine geç.

GameNav, Blender 4.2 ve üzeri sürümler için paketlenmiştir.

## Kullanım

3D Viewport üzerindeyken `Shift + F` tuşlarına bas veya GameNav panelindeki **WASD Gezinmeyi Başlat** düğmesini kullan.

| Kontrol | İşlev |
| --- | --- |
| `W A S D` / Oklar | Hareket |
| Mouse | Bakış |
| `E / Q` | Yukarı / Aşağı |
| `Shift` | Hızlan |
| `Alt` | Yavaş ve hassas hareket |
| Mouse tekerleği | Anlık hızı artır / azalt |
| Sol tık / Enter | Yeni görünümü koruyup çık |
| Esc / Sağ tık | Başlangıç görünümüne dönüp çık |

Kısayolu değiştirmek için **Edit > Preferences > Keymap** altında `GameNav` veya `GameNav Başlat` araması yapabilirsin.

## Geliştirme

Kaynak klasörünün kökünde hem `__init__.py` hem de `blender_manifest.toml` bulunur. Blender'ın güncel extension sistemiyle doğrudan paketlenebilir:

```text
blender --command extension build
```

## Lisans

GPL-3.0-or-later. Ayrıntılar için `LICENSE` dosyasına bak.
