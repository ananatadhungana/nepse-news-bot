import ai_filter, datetime
now = datetime.datetime.now(datetime.timezone.utc)
ago = lambda h: (now - datetime.timedelta(hours=h)).isoformat()
sent = [(5, "अतिकम विकसित मुलुकको सूचीबाट स्तोरन्नति हुन नेपालले पायो २०२९ नोभेम्बर २४ सम्मको मिति"),
        (4, "Kamala Bridge set to open by December, says minister"),
        (3, "आजदेखि ८ दिनसम्म काठमाडौँका यी स्थानमा साढे ५ घण्टा विद्युत् आपूर्ति बन्द हुने"),
        (3, "नेपाल टेलिकममा ८० पदका लागि रोजगारीको अवसर, कसले दिन पाउँछन् आवेदन ?"),
        (2, "सुन तोलामा ३ हजार २ सय रुपैयाँ घट्यो"),
        (26, "सुनको मूल्य तोलामा २ हजार बढ्यो"),
        (6, "नेप्से २५ अंकले घट्यो, कारोबार ४ अर्ब"),
        (8, "नबिल बैंकको साधारण सभा मंसिर ५ गते")]
hist = [{'link': f's{i}', 'headline': h, 'sent_at': ago(a)} for i, (a, h) in enumerate(sent)]
new = [("UN extends Nepal, Bangladesh LDC graduation preparatory period until 2029", True),
       ("नेपाल र बंगलादेशको एलडीसी स्तरोन्नतिको तयारी अवधि २०२९ नोभेम्बर २४ सम्म थप", True),
       ("नेपाललाई अतिकम विकसित मुलुकबाट स्तरोन्नतिका लागि तयारी अवधि ३ वर्ष थप", True),
       ("कमला पुल मंसिर पहिलो साताभित्र सञ्चालनमा ल्याउने गरी काम भइरहेको छ : मन्त्री लम्साल", True),
       ("आजदेखि काठमाडौंका यी क्षेत्रमा ८ दिनसम्म बिजुली काटिने, कुन दिन कहाँ?", True),
       ("टेलिकमले माग्यो नवौँ तहको इन्जिनियरदेखि जुनियर टेक्निसियनसम्मका ८० कर्मचारी", True),
       ("Gold price drops by Rs 3,200", True),
       ("सुनको मूल्य तोलामा ३ हजार ५ सय बढ्यो", False),
       ("नेप्से ४० अंकले बढ्यो, कारोबार ६ अर्ब", False),
       ("नबिल बैंकले १५ प्रतिशत लाभांश प्रस्ताव गर्‍यो", False),
       ("एनसेलमा ५० पदका लागि रोजगारी", False),
       ("राष्ट्र बैंकले नीतिगत ब्याजदर घटायो", False)]
cand = [{'link': f'n{i}', 'headline': h, 'source': 'T'} for i, (h, _) in enumerate(new)]
d = ai_filter.find_dupes(cand, hist, {})
ok = 0
for i, (h, exp) in enumerate(new):
    got = f'n{i}' in d
    ok += got == exp
    print(('OK  ' if got == exp else 'MISS'), 'dup' if got else 'new', '|', h[:70])
print(f'SCORE {ok}/{len(new)}')
