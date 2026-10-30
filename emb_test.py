import os, requests, math
KEY = os.environ['GEMINI_API_KEY']; H = {'x-goog-api-key': KEY, 'Content-Type': 'application/json'}
ms = requests.get('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', headers=H).json().get('models', [])
emb_models = [m['name'] for m in ms if 'embedContent' in m.get('supportedGenerationMethods', [])]
print('EMBED MODELS', emb_models)
DUP = [("सरकारले १२० वटा फर्म तथा कम्पनीलाई कालोसूचीमा राख्यो","Government Blacklists 120 Firms for Procurement Violations"),
("Nepal Telecom opens applications for 80 vacancies across various positions","नेपाल टेलिकममा ८० पदका लागि रोजगारीको अवसर, कसले दिन पाउँछन् आवेदन ?"),
("दिनेश थकाली बने डेभलपमेन्ट बैंकर्स एसोसिएसनको अध्यक्ष","विकास बैंक संघको अध्यक्षमा दिनेश थकाली, ९ सदस्यीय कार्यसमितिमा को को भए निर्वाचित"),
("Karnali Province's Economic Growth Estimated at 2.94% in FY 2082/83: NRB Report","कर्णालीको आर्थिक वृद्धि २.९४ मात्रै, राडीपाखी उत्पादन सबैभन्दा राम्रो"),
("स्वाभिमान लघुवित्तले १:१ को अनुपातमा हकप्रद सेयर जारी गर्ने, बोलायो १०औं साधारण सभा","स्वाभिमान लघुवित्तको पुँजी दोब्बर बनाउने प्रस्ताव, मर्जर पनि एजेन्डामा"),
("समस्याग्रस्त कर्णालीका संस्थापकको सेयर स्वामित्व १% मा झारियो, दाबी विरोध भए प्रमाणसहित","कर्णाली डेभलपमेन्ट बैंकका ३५ शेयरधनीको शेयर पूँजी १ प्रतिशतमा झारियो, मंसिर ९ गते"),
("Stock market fails to hold above 2,700, trading highest in seven months","करिब ९ अर्बको सेयर कारोबार, नेप्से २७ सय नजिक"),
("वैदेशिक लगानी प्रतिबद्धता तीन महिनामा १६.२३ अर्बको, धेरै परियोजना सूचना प्रविधि","FDI pledges decline by more than half to Rs 16.23 billion in Q1"),
("Country’s public debt exceeds Rs 30 trillion","सार्वजनिक ऋण नाघ्यो ३० खर्ब, प्रत्येक नेपालीको भागमा १ लाख ऋणभार"),
("Gold price drops by Rs 3,200","सुनको मूल्यमा एकैदिन ३२ सयको गिरावट, चाँदीको मुल्य पनि घट्यो"),
("Kamala Bridge set to open by December, says minister","कमला पुल मंसिर पहिलो साताभित्र सञ्चालनमा ल्याउने गरी काम भइरहेको छ : मन्त्री लम्साल"),
("यी ६ निर्माण कम्पनी परे प्रधानमन्त्री कार्यालयको कालो सूचीमा","६ निर्माण व्यवसायी र आपूर्तिकर्ता कालोसूचीमा(सूचीसहित)"),
("कर, शुल्क र जरिबाना मिनाहा हुने म्याद पुस मसान्तसम्म थप","म्यादभित्र विवरण नबुझाएका कम्पनीलाई कर बुझाउने समय पुस मसान्तसम्म थपियो, जरिबाना मिनाहा"),
("भाटभटेनीले अघि सार्‍यो ईभी योजना, फोटोनका १२ गाडीबाट ढुवानी सुरू","Bhatbhateni Supermarket Introduces Electric Vehicles for Fresh Produce Delivery"),
("Irrigation department chief and Sunkoshi Marin project director detained","सुनकोशी मरिणको ठेक्का प्रक्रिया रद्द गर्न नमान्दा सिँचाइ महानिर्देशक प्रहरी नियन्त्रणमा"),
("विदेशी मुद्रा विनिमयदर: अमेरिकी डलरको खरिददर १५२.१२, अरू कुन देशको कति ?","आज पाउण्डको बिक्री मूल्य २०३.३२ रुपैयाँ, अन्य विदेशी मुद्राको विनिमय दर कति?")]
NOT = [("साताको सुनः १८ सय रुपैयाँले बढ्यो मूल्य","सुन तोलामा ३ हजार २ सय रुपैयाँ घट्यो"),
("सुनको मूल्य तोलामा २ हजार बढ्यो","सुनको मूल्य तोलामा ३ हजार ५ सय बढ्यो"),
("नेप्से २५ अंकले घट्यो, कारोबार ४ अर्ब","नेप्से ४० अंकले बढ्यो, कारोबार ६ अर्ब"),
("नबिल बैंकको साधारण सभा मंसिर ५ गते","नबिल बैंकले १५ प्रतिशत लाभांश प्रस्ताव गर्‍यो"),
("Commercial banks issue loans of Rs 141 billion in first quarter of FY 2026/27","बागमतीमा मात्रै बैंकको ५२ खर्ब निक्षेप, कर्णालीमा १ खर्ब ११ अर्ब मात्रै"),
("कर्णाली प्रदेश : औद्योगिक कर्जा २५.६३ प्रतिशतले बढ्यो, उद्योगको क्षमता उपयोग ३१","कर्णालीको आर्थिक वृद्धि २.९४ मात्रै, राडीपाखी उत्पादन सबैभन्दा राम्रो"),
("Nepal Telecom opens applications for 80 vacancies across various positions","एनसेलमा ५० पदका लागि रोजगारी"),
("राष्ट्र बैंकले नीतिगत ब्याजदर घटायो","राष्ट्र बैंकद्वारा १६ सहकारीको अनुगमन, कर्जामा देखिए नियमविपरीतका गतिविधि"),
("Government Blacklists 120 Firms for Procurement Violations","यी ६ निर्माण कम्पनी परे प्रधानमन्त्री कार्यालयको कालो सूचीमा"),
("स्वाभिमान लघुवित्तको पुँजी दोब्बर बनाउने प्रस्ताव, मर्जर पनि एजेन्डामा","सारथी इक्विटी फण्डले शेयरधनीलाई १० प्रतिशत नगद लाभांश दिने"),
("Kamala Bridge set to open by December, says minister","कोशी ब्यारेजको विकल्पमा ४३ अर्बको नयाँ पुल बनाउने तयारी")]
def cos(a,b): return sum(x*y for x,y in zip(a,b))/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
for m in [x for x in emb_models if 'embedding' in x][:3]:
    texts=[t for p in DUP+NOT for t in p]
    body={'requests':[{'model':m,'content':{'parts':[{'text':t}]},'taskType':'SEMANTIC_SIMILARITY','outputDimensionality':256} for t in texts]}
    r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/{m}:batchEmbedContents',headers=H,json=body)
    if r.status_code!=200: print(m,'HTTP',r.status_code,r.text[:200]); continue
    v=[e['values'] for e in r.json()['embeddings']]
    print('\n###',m,'dim',len(v[0]))
    s=[cos(v[2*i],v[2*i+1]) for i in range(len(DUP)+len(NOT))]
    print('DUP ',sorted(round(x,3) for x in s[:len(DUP)]))
    print('NOT ',sorted(round(x,3) for x in s[len(DUP):]))
    for (a,b),x in zip(DUP+NOT,s): print(f'{x:.3f}', 'D' if (a,b) in DUP else 'N', a[:40],'|',b[:40])
