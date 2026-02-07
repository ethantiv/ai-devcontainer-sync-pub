usprawnienie trybu developerskiego (zmienna środowiskowa DEV_MODE), oprócz wyłącznie w trybie developerskim bota telegram ma on też ustawiać:
- na potrzeby coolify nazwa obrazu, kontenera, serwisu musi się różnić od nazwy zbudowanej z gałęzi main, dla main claude-code, dla dev_mode dev-claude-code
- muszą działać poprawnie aliasy cc i dev-cc na mirek@raspberrypi.local dla obu kontenerów których nazwy mają losowe sufixy w nazwie kontenera dlatego część stała musi być inna, jak wyżej wspomniano dev-claude-code i claude-code

przeprowadź w fazie planowania reasearch dokumentacji coolify (contex7/web/agent-browser) dla poprawnego deploymentu serwisów w wersjach dev/prod (nie chcę tworzyć osobnych środowisk na coolify, ma to być obsłużone w ramacha jednego środowiska na raspberrypi)