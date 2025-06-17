# Benzerlik Algoritmaları

## Giriş

AutoSo'nun yüksek doğruluğunun arkasındaki sır, tek bir benzerlik ölçütüne bağlı kalmak yerine, iki farklı ve birbirini tamamlayan yaklaşımı birleştiren **hibrit bir model** kullanmasıdır. Gerçek dünyada bir sunum sırasında iki temel hata türü ortaya çıkabilir:

1.  **Konuşmacı Hataları:** Konuşmacı metinden sapabilir, eş anlamlı kelimeler kullanabilir veya cümleleri yeniden ifade edebilir.
2.  **STT (Speech-to-Text) Hataları:** Konuşma tanıma motoru, duyduğu sesi yanlış yazıya dökebilir (örn: "right" yerine "write").

Bu iki sorunu çözmek için AutoSo, hem anlamsal hem de fonetik benzerliği ölçer. `speech_matcher.py` dosyasındaki `SpeechMatcher` sınıfı, bu iki algoritmanın sonuçlarını birleştirerek nihai kararı verir.

## Hibrit Model: Semantik ve Fonetik Birleşimi

`SpeechMatcher` sınıfı, iki algoritmadan gelen sonuçları, önceden belirlenmiş ağırlıklarla birleştirir:

-   **%40 Semantik Benzerlik**
-   **%60 Fonetik Benzerlik**

Bu ağırlıklandırma, STT hatalarının (fonetik sapmalar) konuşmacının kelime seçimi değişikliklerinden (semantik sapmalar) daha yaygın ve navigasyon için daha kritik olduğu varsayımına dayanır. `_combine_results` metodu, her bir aday chunk için bu ağırlıklı ortalamayı hesaplar ve en yüksek skora sahip olanları sıralar.

---

## Bölüm 1: Semantik Benzerlik (`semantic.py`)

### Amaç

Semantik benzerliğin temel amacı, metinlerin **anlamlarına** dayalı olarak ne kadar yakın olduğunu ölçmektir. Bu, konuşmacının metne birebir sadık kalmadığı, ancak aynı anlama gelen farklı kelimeler kullandığı durumları yakalamak için hayati önem taşır.

-   **Örnek Senaryo:**
    -   Transkriptteki Chunk: `"start with a question"`
    -   Konuşmacının Söylediği: `"begin with an inquiry"`
    -   *Sonuç:* Metinler tamamen farklı olsa da, anlamları neredeyse aynıdır. Semantik algoritma burada yüksek bir skor üretecektir.

### Nasıl Çalışır?

1.  **Model:** Sistem, `model2vec` kütüphanesi aracılığıyla, `minishlab/potion-base-2M` gibi, metinleri anlamlı sayısal vektörlere dönüştürmek için eğitilmiş bir dil modeli kullanır.
2.  **Embedding (Gömme):** Her bir metin (hem konuşmacıdan gelen sorgu hem de aday chunk'lar), bu model kullanılarak çok boyutlu bir vektöre (embedding) dönüştürülür. Bu vektör, metnin anlamsal "özünü" temsil eder.
3.  **Kosinüs Benzerliği:** İki metnin ne kadar benzer olduğunu ölçmek için, vektörleri arasındaki açıya bakılır. `calculate_similarity` metodu, sorgu vektörü ile her bir aday chunk'ın vektörü arasındaki kosinüs benzerliğini hesaplar. Vektörler birbirine ne kadar yakınsa, skor 1'e o kadar yaklaşır.

### Performans Optimizasyonu: LRU Cache

Sürekli aynı kelimeler veya ifadeler için embedding hesaplamak verimsizdir. `Semantic` sınıfı, bu sorunu çözmek için bir **LRU (Least Recently Used) Cache** (`embedding_cache`) mekanizması kullanır.
-   Bir metnin embedding'i bir kez hesaplandığında, bu sonuç bellekte saklanır.
-   Aynı metin tekrar geldiğinde, embedding yeniden hesaplanmak yerine doğrudan bellekten okunur.
-   Bu, özellikle sık tekrar eden ifadeler olduğunda sistemin performansını önemli ölçüde artırır.

---

## Bölüm 2: Fonetik Benzerlik (`phonetic.py`)

### Amaç

Fonetik benzerliğin temel amacı, metinlerin **sesletimlerine (telaffuzlarına)** dayalı olarak ne kadar benzediğini ölçmektir. Bu, STT motorunun kelimeleri yanlış yazıya döktüğü ancak sesletim olarak benzer kelimeler ürettiği durumları yakalamak için kritik öneme sahiptir.

-   **Örnek Senaryo:**
    -   Transkriptteki Chunk: `"let me see your hands"`
    -   STT Çıktısı: `"let me see **your hence**"`
    -   *Sonuç:* "hands" ve "hence" kelimeleri anlamsal olarak tamamen farklıdır, ancak fonetik olarak birbirine çok benzer. Fonetik algoritma burada yüksek bir skor üreterek STT hatasını tolere edecektir.

### Nasıl Çalışır?

`Phonetic` sınıfı, standart metin karşılaştırma algoritmalarından daha gelişmiş, sese duyarlı bir yaklaşım kullanır:

1.  **Fonetik Gruplar (`_phonetic_groups`):** Algoritma, benzer seslere sahip harfleri aynı gruba atar. Örneğin:
    -   `A, E, I, O, U, Y` -> Grup 0 (sesli harfler)
    -   `B, P` -> Grup 1
    -   `C, K, Q` -> Grup 2
    -   `D, T` -> Grup 3
2.  **Ağırlıklı Düzeltme Mesafesi (Weighted Edit Distance):** Sistem, iki kelime arasındaki farkı hesaplarken (örn: `_word_edit_distance`), harf değiştirme maliyetini bu gruplara göre belirler.
    -   Aynı gruptaki harflerin birbirine dönüşme maliyeti düşüktür (örn: `B` -> `P`).
    -   Farklı gruplardaki harflerin dönüşme maliyeti yüksektir (örn: `B` -> `S`).
3.  **Skorlama:** İki metin arasındaki toplam fonetik mesafe ne kadar düşükse, fonetik benzerlik skoru o kadar yüksek olur.

### Performans Optimizasyonu: Fonksiyon Önbellekleme

Fonetik hesaplamalar yoğun olabilir. Performansı artırmak için, `_word_edit_distance`, `_compute_distance` gibi çekirdek hesaplama fonksiyonları Python'un `@lru_cache` dekoratörü ile sarmalanmıştır. Bu, aynı kelime veya metin çiftleri için yapılan hesaplamaların sonuçlarının bellekte tutulmasını ve tekrar tekrar hesaplanmasını önleyerek önemli bir hız artışı sağlar.