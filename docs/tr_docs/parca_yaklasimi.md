# Chunk (Parça) Üretim Yaklaşımı

## Giriş

**Chunk**, AutoSo'nun gerçek zamanlı eşleştirme motorunun temel yapı taşıdır. Bir "chunk", tam transkriptin küçük, örtüşen bir metin parçasıdır. Sistem, uzun ve karmaşık cümleleri doğrudan eşleştirmeye çalışmak yerine, bu kısa ve yönetilebilir chunk'ları kullanarak çok daha hızlı, esnek ve hataya dayanıklı bir navigasyon sağlar.

Bu belgede, `chunk_generator.py` dosyasında uygulanan ve bir `..._transcript.json` dosyasından yola çıkarak bu chunk'ların nasıl oluşturulduğu detaylı bir şekilde açıklanmaktadır.

## Chunk Yapısının Anatomisi

Oluşturulan her bir chunk, basit bir metin parçasından daha fazlasıdır. Sistem için gerekli olan kritik meta verileri içerir:

-   `chunk_index`: Chunk'ın tüm chunk'lar listesindeki sırasını belirten tam sayı.
-   `chunk_id`: `fastnanoid` ile oluşturulmuş, her bir chunk için benzersiz olan kimlik.
-   `source_transcripts`: Bu chunk'ı oluşturan kelimelerin hangi orijinal transkript(ler)den geldiğini belirten `transcript_id` listesi. Bu, sistemin en önemli bağlamsal bilgisidir.
-   `chunk`: 7 kelimeden oluşan asıl metin içeriği.

## Üretim Süreci (`ChunkGenerator` Sınıfı)

`ChunkGenerator` sınıfı, transkriptleri chunk'lara dönüştürme işlemini yönetir. Süreç, yüksek verimlilik için paralel olarak çalışacak şekilde tasarlanmıştır.

### Adım 1: Transkript Verisinin Yüklenmesi

Süreç, bir önceki adımda oluşturulan `kullanici_adi_transcript.json` dosyasının okunmasıyla başlar. Transkriptler, `transcript_index`'e göre sıralanarak işlem sırasının korunması sağlanır.

### Adım 2: Kelimelerin Birleştirilmesi (`_get_words` metodu)

Tüm transkriptler tek bir havuzda birleştirilir. Ancak bu birleştirme sırasında her bir kelimenin nereden geldiği bilgisi korunur. Sistem, tüm transkriptleri tarayarak aşağıdaki gibi bir "kelime nesneleri" listesi oluşturur:

```python
[
    {'text': 'the', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    {'text': 'ability', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    {'text': 'to', 'source_transcript': 'iqM_H_XCm0rUW_46obYGl', 'transcript_index': 0},
    # ...
    {'text': 'someone', 'source_transcript': 'L9LPKs2roR5FOS6HhPiRP', 'transcript_index': 1},
    # ...
]
```
Bu yapı, her kelimenin kökenini bilmemizi sağlar.

### Adım 3: Kayan Pencere (Sliding Window) Tekniği

Bu, chunk üretiminin özünü oluşturan tekniktir. Sistem, `window_size` parametresi (varsayılan olarak **7**) ile tanımlanan bir pencereyi, birleşik kelime listesi üzerinde birer birer kaydırır.

**Görselleştirme:**
Eğer kelime listesi `W1, W2, W3, W4, W5, W6, W7, W8, W9, ...` ise, oluşturulan chunk'lar şunlar olacaktır:
-   **Chunk 1:** `W1 W2 W3 W4 W5 W6 W7`
-   **Chunk 2:** `W2 W3 W4 W5 W6 W7 W8`
-   **Chunk 3:** `W3 W4 W5 W6 W7 W8 W9`
-   ... ve bu şekilde devam eder.

Bu örtüşme (overlap), konuşmacının konuşmasının herhangi bir 7 kelimelik bölümünün mutlaka bir chunk ile eşleşme potansiyeline sahip olmasını garanti eder.

### Adım 4: Kaynak Takibi ve Kimliklendirme

Her bir pencere için aşağıdaki işlemler yapılır:

1.  **Metin Oluşturma:** Penceredeki 7 kelime birleştirilerek `chunk` metni oluşturulur.
2.  **Kaynak Tespiti:** Penceredeki 7 "kelime nesnesinin" `source_transcript` alanları incelenir. Bu listedeki benzersiz `transcript_id`'ler toplanır ve `source_transcripts` listesine eklenir.
    -   **Kritik Not:** Eğer bir pencere, iki transkriptin birleşim noktasına denk gelirse (örneğin, ilk 4 kelime `transcript_id_A`'dan, son 3 kelime `transcript_id_B`'den geliyorsa), `source_transcripts` listesi her iki kimliği de içerir: `["transcript_id_A", "transcript_id_B"]`. Bu, navigasyon algoritmasının geçiş anlarını hassas bir şekilde yakalamasını sağlar.
3.  **Kimliklendirme:** Her yeni chunk'a `fastnanoid` ile benzersiz bir `chunk_id` ve sırasını belirten `chunk_index` atanır.

### Adım 5: Kayıt

Oluşturulan tüm chunk'ların listesi, `orjson` kullanılarak `kullanici_adi_chunks.json` dosyasına kaydedilir.

### Nihai Çıktı

Sonuç olarak, navigasyon motorunun besleyeceği, zengin meta veriye sahip bir chunk listesi elde edilir:
```json
[
  {
    "chunk_index": 10,
    "chunk_id": "a8bJ0T0urzKnJwXSBoxfX",
    "source_transcripts": [
      "L9LPKs2roR5FOS6HhPiRP"
    ],
    "chunk": "you tried to say no to someone"
  },
  {
    "chunk_index": 11,
    "chunk_id": "NGgQvJTu5k38DCk9TQYf_",
    "source_transcripts": [
      "L9LPKs2roR5FOS6HhPiRP",
      "VIf3Xfh6hTseWFS3zaTuU"
    ],
    "chunk": "tried to say no to someone or"
  }
]
```
Bu yapı, sistemin sadece "ne söylendiğini" değil, aynı zamanda "sunumun neresinde söylendiğini" de bilmesini sağlar.