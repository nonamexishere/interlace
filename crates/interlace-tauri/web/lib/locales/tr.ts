import type { ChromePack } from "./en";

/** Turkish UI chrome. Message bodies / names / snippets are not in this pack. */
export const tr: ChromePack = {
  openArchive: "Arşiv aç",
  openAnArchive: "Arşiv aç",
  openExisting: "Arşiv aç",
  createArchive: "Arşiv oluştur…",
  doctor: "Doktor",
  people: "Kişiler",
  search: "Ara",
  searchPlaceholder: "Mesajlarda ara",
  review: "İnceleme",
  import: "İçe aktar",
  accept: "Kabul",
  reject: "Reddet",
  noPeopleYet: "Henüz kişi yok",
  selectAPerson: "Bir kişi seçin",
  noDoctorIssues: "Doktor sorunu yok",
  nothingToReview: "İncelenecek bir şey yok",
  reviewEmptyBody:
    "Yalnızca ada göre WhatsApp eşleşmeleri burada görünür. Asla otomatik birleşmez. Kuyruk bekliyorsanız Kişiler içe aktarın.",
  loadingReviewQueue: "İnceleme kuyruğu yükleniyor…",
  linkThesePeople: "Bu kişileri bağla?",
  linkThesePeopleDesc: "{n} kişiyi tek kişide birleştir. Mesajlar yerinde kalır.",
  stopSuggesting: "Bu çifti önermeyi bırak?",
  stopSuggestingDesc: "Bu kişiler bir daha önerilmez.",
  undoLastLink: "Son bağlantıyı geri al",
  undoLastLinkConfirm: "Son bağlantıyı geri al?",
  undoLastLinkDesc:
    "Son kimlik grafiği değişikliğini geri alır. Mesajlar yerinde kalır.",
  undoing: "Geri alınıyor…",
  typeAQuery: "Bir sorgu yazın",
  noHits: "Sonuç yok",
  searchFilters: "Filtreler",
  searchFrom: "Başlangıç",
  searchTo: "Bitiş",
  searchDateInvalid:
    "Tarih aralığını kontrol edin. Başlangıç ve bitiş geçerli olmalı; başlangıç bitişten sonra olamaz.",
  openingLastArchive: "Son arşiv açılıyor",
  noFileSelected: "Dosya seçilmedi",
  importEmptyBody:
    "Bir WhatsApp ZIP, Takeout klasörü, mbox veya kişiler dosyası seçin. Yalnızca klasör seçici — URL yok.",
  pickFile: "Dosya seç",
  pickFileEllipsis: "Dosya seç…",
  cancel: "İptal",
  backupUnit: "Yedek birimi klasördür.",
  notEncryptedAtRest: "Diskte şifreli değil. Şifrelemeniz FileVault.",
  noSeparateBackup: "Ayrı bir yedek komutu yok.",
  doNotKeepLive:
    "Canlı arşivi iCloud Drive, Dropbox veya Google Drive'da tutmayın.",
  timeMachineOk:
    "Bu pencereyi kapattıktan sonra tüm klasörün Time Machine yedeği uygundur. Bakınız",
  cloudBanner:
    "Bu arşiv iCloud, Dropbox veya Google Drive üzerinde duruyor gibi görünüyor.",
  doctorPaneLead:
    "Aynı kontroller interlace doctor. Bu pencere arşiv kilidini tutuyor — terminalde doctor çalıştırmadan önce kapatın.",
  doctorEmptyBody:
    "SQLite, FTS ve başvurulan CAS blob'ları sağlıklı görünüyor. Başvurulmayan dosyalar silinsin istiyorsanız hâlâ CAS GC gerekir.",
  runIntegrityCheck: "Bütünlük denetimi çalıştır?",
  runIntegrityCheckDesc:
    "Salt okunur PRAGMA integrity_check ve FTS bütünlüğü. Mesajları değiştirmez.",
  integrityCheck: "Denetle",
  integrityCheckFinished: "Bütünlük denetimi bitti.",
  rebuildSearchIndex: "Arama dizinini yeniden oluştur?",
  rebuildSearchIndexDesc:
    "Eksikse FTS tetikleyicilerini yeniden kurar ve dizini oluşturur. Mesajlar ve CAS yerinde kalır.",
  rebuild: "Yeniden oluştur",
  ftsRebuildFinished: "FTS yeniden oluşturma bitti.",
  gcUnusedCas: "Kullanılmayan CAS dosyalarını çöp topla?",
  gcUnusedCasDesc:
    "Ekler veya kişi fotoğrafları tarafından başvurulmayan blob'ları siler. Geri alınamaz. Önce diğer yazıcıları kapatın.",
  deleteUnused: "Kullanılmayanı sil",
  casGcFinished: "CAS GC bitti.",
  copyText: "Metni kopyala",
  revealInFinder: "Finder'da göster",
  collapseSidebar: "Kişi kenar çubuğunu daralt",
  expandSidebar: "Kişi kenar çubuğunu genişlet",
  inspector: "İnceleyici",
  identities: "Kimlikler",
  lastActivity: "Son etkinlik",
  findInThread: "Sohbette bul",
  jumpToDay: "Güne git",
};
