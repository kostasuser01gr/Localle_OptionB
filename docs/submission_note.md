# Σύντομο σημείωμα παράδοσης — Επιλογή Β

Σχεδίασα τον αυτοματισμό ως μικρό **reservation intake system** και όχι ως απλό email parser. Κάθε Gmail thread αντιστοιχεί σε ένα αίτημα κράτησης: το AI εξάγει τα στοιχεία σε αυστηρό schema, deterministic logic αποφασίζει αν το αίτημα είναι `READY`, `NEEDS_INFO` ή `HUMAN_REVIEW`, και το Google Sheet ενημερώνει την ίδια γραμμή όταν ο πελάτης συνεχίζει τη συζήτηση.

Η πρώτη απάντηση επιβεβαιώνει μόνο όσα έχουν πράγματι κατανοηθεί και ζητά μόνο τα απαραίτητα στοιχεία που λείπουν. Αν αναφερθεί φθηνότερη ανταγωνιστική προσφορά, γίνεται ουδέτερη σύγκριση του τελικού κόστους/όρων χωρίς επίθεση σε ανταγωνιστή και χωρίς επινόηση live τιμής. Δεν επιτρέπεται αυτόματη επιβεβαίωση διαθεσιμότητας, κράτησης ή συγκεκριμένου οχήματος χωρίς πραγματική πηγή δεδομένων.

Πρόσθεσα message-id idempotency, συνέχεια conversation ανά thread, human-review queue, auto-reply/bounce protection, bounded AI retries, audit trail και δύο επίπεδα ελέγχου του εξερχόμενου email (semantic verifier + deterministic multilingual guard). Το auto-send είναι κλειστό by default και ενεργοποιείται από το `Config` Sheet μόνο μετά από ελεγχόμενο test.

Με περισσότερο χρόνο/πραγματική πρόσβαση σε σύστημα πελάτη, το επόμενο βήμα θα ήταν σύνδεση με πραγματικό availability/pricing/fleet API και μεταφορά του transactional state από Google Sheets σε transactional database για hard exactly-once semantics.
