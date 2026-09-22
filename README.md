# Pallet Sorting Manager

Streamlit appka na spravu pravidiel smerovania paliet a testovanie vyslednej lokacie.

## Ukladanie pravidiel

Appka vie bezat v dvoch rezimoch:

- ked nie je nastavene `DATABASE_URL`, pravidla sa ukladaju lokalne do `rules.csv`;
- ked je nastavene `DATABASE_URL`, pravidla sa ukladaju do centralnej PostgreSQL databazy a zmeny vidi kazdy pouzivatel online appky.

Pri prvom spusteni s prazdnou databazou sa pravidla inicializuju z `rules.csv`.

## Lokalne spustenie

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Nasadenie online

Najjednoduchsia cesta je Streamlit Community Cloud alebo Render:

1. nahraj repozitar na GitHub,
2. vytvor PostgreSQL databazu, napriklad Neon alebo Render Postgres,
3. v nastaveniach appky pridaj secret alebo environment variable `DATABASE_URL`,
4. nastav hlavny subor appky na `streamlit_app.py`.

Po nasadeni sa pridane, upravene aj zmazane pravidla ukladaju do centralnej databazy.
