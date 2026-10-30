import json, datetime as dt, ai_filter
now = dt.datetime.now(dt.timezone.utc)
hist = json.load(open('sent_news.json', encoding='utf-8'))
# pool: real channel history, minus every test headline, aged 1-30h
TESTS = [  # (already-sent side, new side, expected dup)
("सरकारले १२० वटा फर्म तथा कम्पनीलाई कालोसूचीमा राख्यो","Government Blacklists 120 Firms for Procurement Violations",True),
("नेपाल टेलिकममा ८० पदका लागि रोजगारीको अवसर, कसले दिन पाउँछन् आवेदन ?","Nepal Telecom opens applications for 80 vacancies across various positions",True),
("दिनेश थकाली बने डेभलपमेन्ट बैंकर्स एसोसिएसनको अध्यक्ष","विकास बैंक संघको अध्यक्षमा दिनेश थकाली, ९ सदस्यीय कार्यसमितिमा को को भए निर्वाचित",True),
("Karnali Province's Economic Growth Estimated at 2.94% in FY 2082/83: NRB Report","कर्णालीको आर्थिक वृद्धि २.९४ मात्रै, राडीपाखी उत्पादन सबैभन्दा राम्रो",True),
("स्वाभिमान लघुवित्तले १:१ को अनुपातमा हकप्रद सेयर जारी गर्ने, बोलायो १०औं साधारण सभा","स्वाभिमान लघुवित्तको पुँजी दोब्बर बनाउने प्रस्ताव, मर्जर पनि एजेन्डामा",True),
("समस्याग्रस्त कर्णालीका संस्थापकको सेयर स्वामित्व १% मा झारियो, दाबी विरोध भए प्रमाणसहित","कर्णाली डेभलपमेन्ट बैंकका ३५ शेयरधनीको शेयर पूँजी १ प्रतिशतमा झारियो, मंसिर ९ गते",True),
("करिब ९ अर्बको सेयर कारोबार, नेप्से २७ सय नजिक","Stock market fails to hold above 2,700, trading highest in seven months",True),
("वैदेशिक लगानी प्रतिबद्धता तीन महिनामा १६.२३ अर्बको, धेरै परियोजना सूचना प्रविधि","FDI pledges decline by more than half to Rs 16.23 billion in Q1",True),
("सार्वजनिक ऋण नाघ्यो ३० खर्ब, प्रत्येक नेपालीको भागमा १ लाख ऋणभार","Country’s public debt exceeds Rs 30 trillion",True),
("सुन तोलामा ३ हजार २ सय रुपैयाँ घट्यो","Gold price drops by Rs 3,200",True),
("Kamala Bridge set to open by December, says minister","कमला पुल मंसिर पहिलो साताभित्र सञ्चालनमा ल्याउने गरी काम भइरहेको छ : मन्त्री लम्साल",True),
("UN extends Nepal, Bangladesh LDC graduation preparatory period until 2029","नेपाललाई अतिकम विकसित मुलुकबाट स्तरोन्नतिका लागि तयारी अवधि ३ वर्ष थप",True),
("आजदेखि ८ दिनसम्म काठमाडौँका यी स्थानमा साढे ५ घण्टा विद्युत् आपूर्ति बन्द हुने","आजदेखि काठमाडौंका यी क्षेत्रमा ८ दिनसम्म बिजुली काटिने, कुन दिन कहाँ?",True),
("कर, शुल्क र जरिबाना मिनाहा हुने म्याद पुस मसान्तसम्म थप","म्यादभित्र विवरण नबुझाएका कम्पनीलाई कर बुझाउने समय पुस मसान्तसम्म थपियो, जरिबाना मिनाहा",True),
(None,"सुनको मूल्य तोलामा ३ हजार ५ सय बढ्यो",False),
(None,"नेप्से ४० अंकले बढ्यो, कारोबार ६ अर्ब",False),
(None,"नबिल बैंकले १५ प्रतिशत लाभांश प्रस्ताव गर्‍यो",False),
(None,"एनसेलमा ५० पदका लागि रोजगारी",False),
(None,"राष्ट्र बैंकले नीतिगत ब्याजदर घटायो",False),
(None,"कोशी ब्यारेजको विकल्पमा ४३ अर्बको नयाँ पुल बनाउने तयारी",False),
(None,"सिद्धार्थ बैंकले १२ प्रतिशत बोनस सेयर दिने",False),
(None,"हिमालयन बैंकको खुद नाफा ३५ प्रतिशतले बढ्यो",False),
]
test_new = {t[1] for t in TESTS} | {t[0] for t in TESTS if t[0]}
pool = [e for e in hist if e['headline'] not in test_new and not e.get('dup')][-300:]
sent = [{'link': e['link'], 'headline': e['headline'], 'sent_at': (now - dt.timedelta(hours=1 + (k % 29))).isoformat()} for k, e in enumerate(pool)]
sent += [{'link': f'old{i}', 'headline': a, 'sent_at': (now - dt.timedelta(hours=3)).isoformat()} for i, (a, b, e) in enumerate(TESTS) if a]
cands = [{'link': f'new{i}', 'headline': b, 'source': 'T'} for i, (a, b, e) in enumerate(TESTS)]
import time; t0 = time.time()
d = ai_filter.find_dupes(cands, sent, {})
ok = 0
for i, (a, b, e) in enumerate(TESTS):
    got = f'new{i}' in d; ok += got == e
    print('OK  ' if got == e else 'MISS', 'dup' if got else 'new', '|', b[:70])
print(f'SCORE {ok}/{len(TESTS)}  pool={len(sent)}  {time.time()-t0:.0f}s')
