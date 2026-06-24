import os
import ssl
import zipfile
import urllib.request
import io
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Setup SSL context for downloading
try:
    ssl_context = ssl._create_unverified_context()
except AttributeError:
    ssl_context = None

DATASET_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "spam_detector_model.joblib")

# Fallback dataset (120 high-quality entries: 60 ham, 60 spam)
FALLBACK_DATA = [
    # --- HAM ---
    ("ham", "Go until jurong point, crazy.. Available only in bugis n great world la e buffet... Cine there got amore wat..."),
    ("ham", "Ok lar... Joking wif u oni..."),
    ("ham", "U dun say so early hor... U c already then say..."),
    ("ham", "Nah I don't think he goes to usf, he lives around here though"),
    ("ham", "Even my brother is not like to speak with me. They treat me like aids patent."),
    ("ham", "As per your request 'Melle Melle (Oru Minnaminunginte Nurungu Vettam)' has been set as your callertune for all Callers. Press *9 to copy your friends Callertune"),
    ("ham", "I'm gonna be home soon and i don't want to talk about this stuff anymore tonight, k? I've cried enough today."),
    ("ham", "I've been searching for the right words to thank you for this breather. I promise i wont take your help for granted and will fulfil my promise. You have been wonderful and a blessing at all times."),
    ("ham", "I HAVE A DATE ON SUNDAY WITH WILL!!"),
    ("ham", "Oh k...i'm watching here:)"),
    ("ham", "Eh u remember how 2 spell his name... Yes i did. He v naughty make until i v wet."),
    ("ham", "Fine if that's the way u feel. That's the way its gota b"),
    ("ham", "Is that seriously how you spell his name?"),
    ("ham", "I'm home. How was your day? Ready for dinner?"),
    ("ham", "Hey, are you free to grab coffee this afternoon around 3?"),
    ("ham", "Can you please buy some eggs and milk on your way back home?"),
    ("ham", "Sorry, I'll be late for the meeting. Start without me."),
    ("ham", "I'm on my way now, should be there in ten minutes."),
    ("ham", "Happy birthday! hope you have an amazing day filled with joy."),
    ("ham", "Yeah, I think we should submit the report by Friday at the latest."),
    ("ham", "Did you see the match last night? What a crazy ending!"),
    ("ham", "I'll call you when I get home, currently driving."),
    ("ham", "Thanks for the help yesterday, I really appreciate it."),
    ("ham", "No problem, glad I could be of assistance. Let me know if you need more help."),
    ("ham", "Are you guys still planning to go camping this weekend?"),
    ("ham", "Tell me when you are ready so I can pick you up."),
    ("ham", "Don't forget to lock the back door before you go to bed."),
    ("ham", "I'm reading that book you recommended. It's really interesting so far!"),
    ("ham", "Just finished dinner, going to watch a movie now."),
    ("ham", "Let's meet at the library around noon to study for the exam."),
    ("ham", "Yeah, that works for me. See you there!"),
    ("ham", "Can we postpone our call to tomorrow? Something urgent came up."),
    ("ham", "Sure, no worries. Hope everything is alright."),
    ("ham", "Good morning! Hope you have a productive day."),
    ("ham", "Haha that was really funny. I will share it with my sister."),
    ("ham", "Where did you put the car keys? I can't find them anywhere."),
    ("ham", "They are on the kitchen counter next to the microwave."),
    ("ham", "Great, thanks! Found them."),
    ("ham", "Do you want me to bring anything for the potluck?"),
    ("ham", "Just bring some drinks or chips, we have plenty of food."),
    ("ham", "Okay, I will grab a couple of bottles of soda."),
    ("ham", "Did you finish the homework for math class?"),
    ("ham", "Almost done, just working on the last problem. It's tricky."),
    ("ham", "I can help you with it if you want. I finished it earlier."),
    ("ham", "That would be awesome, thanks! Let's call in 5 mins."),
    ("ham", "I'm planning to go for a run now, talk to you later."),
    ("ham", "Stay safe and don't forget your water bottle."),
    ("ham", "Hey, did you get the email about the schedule change?"),
    ("ham", "No, what changed? Let me check my inbox."),
    ("ham", "They moved the lecture to 2 PM instead of 10 AM."),
    ("ham", "Oh okay, thanks for letting me know! That gives me more time."),
    ("ham", "Is it raining outside? I need to go to the store."),
    ("ham", "Yes, it is drizzling slightly. Better take an umbrella."),
    ("ham", "Alright, thanks. See you later."),
    ("ham", "Have you heard from Mark recently? He hasn't replied to my text."),
    ("ham", "He mentioned he was going to be busy with family this weekend."),
    ("ham", "Ah that explains it. I'll wait till Monday to follow up."),
    ("ham", "What are your plans for dinner tonight?"),
    ("ham", "Probably just making some pasta. Nothing fancy."),
    ("ham", "Sounds good! Enjoy your evening."),

    # --- SPAM ---
    ("spam", "Free entry in 2 a wkly comp to win FA Cup final tkts 21st May 2005. Text FA to 87121 to receive entry question(std txt rate)T&Cs apply 08452810075over18's"),
    ("spam", "FreeMsg Hey there darling it's been 3 week's now and no word back! I'd like some fun you up for it still? Croft Xmas hrs to sky! txt stop to 61209 or u redeemer sister?"),
    ("spam", "WINNER!! As a valued network customer you have been selected to receivea £900 prize reward! To claim call 09061701461. Claim code KL341. Valid 12 hours only."),
    ("spam", "Had your mobile 11 months or more? U R entitled to Update to the latest colour mobiles with camera for Free! Call The Mobile Update Co FREE on 08002986906"),
    ("spam", "SIX chances to win CASH! From 100 to 20,000 pounds txt> CSH11 and send to 87575. Cost 150p/day, 6days, 16+ TsandCs apply Reply HL 4 info"),
    ("spam", "URGENT! You have won a 1-week FREE membership in our £100,000 Prize Jackpot! Txt the word: CLAIM to No: 81010 T&C www.dbuk.net LCCLTD POBOX 4403LDNW1A7RW18"),
    ("spam", "XXXMobileMovieClub: To use your credit, click the WAP link in the next txt message or click here>> http://wap.xxxmobilemovieclub.com?n=QJKGIGHJJGCBL"),
    ("spam", "England v Macedonia - dont miss the goals/team news. Txt ur national team to 87077 eg ENGLAND to 87077 Try:WALES, SCOTLAND 4txt/ú1.20 POBOXox36504W45WQ 16+"),
    ("spam", "Thanks for your subscription to Ringtone UK your mobile will be charged £5/month Please confirm by replying YES or NO to this message"),
    ("spam", "09061701461 claim code KL341. 1000s of girls waiting to chat! Call now to meet local singles in your area. Calls cost 150p/min."),
    ("spam", "Congratulations! You've won a £500 Amazon Gift Card! Click here to claim your reward now: http://bit.ly/claim500amazon"),
    ("spam", "ALERT: Your bank account has been locked due to suspicious login attempts. Verify your identity immediately at http://secure-banking-login.com"),
    ("spam", "URGENT: Please call 08000930705 immediately. Your credit card application has been approved. Call now to activate your card and receive £100 cash."),
    ("spam", "Get 50% off on all medications! Viagra, Cialis, and more. Online pharmacy. Express shipping. Order now: http://rx-discount-shop.com"),
    ("spam", "Hot local singles are waiting for you! Send a text to 88088 to start chatting. Only £1.50 per message. Reply STOP to opt out."),
    ("spam", "You have 1 new voicemail. Call 09058094507 to listen. Cost 150p/min. To stop notifications text STOP to 80945."),
    ("spam", "Dear customer, your DHL package is waiting for delivery. Please pay the customs fee of £2.99 at http://dhl-tracking-delivery.info to dispatch."),
    ("spam", "Guaranteed loan up to £5000! No credit check required. Apply online in 2 minutes: http://fast-loans-direct.net. Text STOP to opt out."),
    ("spam", "Double your cash in 24 hours! Safe and guaranteed return on investment. Join the bitcoin club now: http://crypto-wealth-club.org"),
    ("spam", "Get FREE ringtones, wallpapers and games for your Nokia! Just text JELLY to 82255. Subscription £3/week. T&Cs apply."),
    ("spam", "URGENT! Your mobile number was selected as the winner of £2000 cash. To claim your prize call 09066362206. Claim code 4432."),
    ("spam", "Final warning: Your Netflix subscription will expire today. Update your payment details to avoid interruption: http://netflix-billing-update.com"),
    ("spam", "Private! Your account has 2000 loyalty points. Redeem them for a brand new Samsung Galaxy phone now! Call 08002988890 to claim."),
    ("spam", "Claim your free spins now! No deposit required. Win real cash today. Register at http://las-vegas-slots-online.com"),
    ("spam", "Important notice: IRS has filed a lawsuit against you. Call 1-800-829-1040 immediately to settle your tax debt and avoid arrest."),
    ("spam", "Congratulations! Your phone number won £1,000,000 in the Coca-Cola Anniversary Promo! Send email to claim@coca-cola.com with code CC99."),
    ("spam", "Get a brand new iPhone 15 for just £1! Limited stock available. Click here to join the raffle: http://iphone15-raffle-promo.com"),
    ("spam", "Make £500 a day working from home! No experience needed. Start earning cash immediately. Register at http://easy-money-jobs.com"),
    ("spam", "ALERT: Someone logged into your PayPal account from Russia. If this wasn't you, reset your password now at http://paypal-security-alert.com"),
    ("spam", "Free ringtone for your mobile! Text TONE to 80160 now. Cost £1.50 per msg. Join the club today!"),
    ("spam", "Your bank account has a pending transfer of £1,500. Click here to accept the funds: http://pending-transfer-secure.com"),
    ("spam", "Lose 10kg in 2 weeks! Revolutionary diet pills. Try it for FREE. Order your trial bottle now: http://weight-loss-miracle.com"),
    ("spam", "Urgent: Your car insurance is expiring. Save up to 50% by switching today. Call 0800-443-8899 for a free quote."),
    ("spam", "Congratulations! You have been selected for a free cruise to the Bahamas. Text YES to 87077 to claim. T&Cs apply."),
    ("spam", "Get cheap flights to anywhere in the world! Subscribe to our newsletter now. Reply TRAVEL to 82244. £1/week."),
    ("spam", "Your utility bill is overdue. Avoid service disconnection by paying your balance of £84.20 immediately at http://utility-bill-pay.com"),
    ("spam", "Win a brand new BMW 3 Series! Text CAR to 85050 to enter the draw. Entry fee £2/msg. 18+ only."),
    ("spam", "URGENT: Your parcel from Amazon has been held at the sorting office. Click here to schedule redelivery: http://amazon-parcel-held.com"),
    ("spam", "Get unlimited access to adult mobile games! Text PLAY to 89955. Subscription £4.50/week. Reply STOP to cancel."),
    ("spam", "We tried to deliver your parcel today but no one was home. Please choose a new delivery slot here: http://post-office-redelivery.info"),
    ("spam", "Earn extra income by driving your car with our advertising stickers. Up to £300/week. Register at http://wrap-ads-car.com"),
    ("spam", "Your Apple ID has been suspended due to security reasons. Verify your account immediately at http://apple-id-verify-secure.com"),
    ("spam", "Win £500 shopping voucher for Sainsbury's! Take our 1-minute survey now: http://sainsburys-voucher-survey.net"),
    ("spam", "Final call: Claim your £250 cashback reward from O2. Click here: http://o2-cashback-reward.com. Offer ends tonight!"),
    ("spam", "Get the lowest rates on mortgages! Save thousands on your home loan. Free consultation: http://mortgage-rates-expert.net"),
    ("spam", "URGENT: You are pre-approved for a Visa credit card with a £5000 limit. Apply now: http://visa-credit-card-apply.net"),
    ("spam", "Join the elite traders club! Make 300% profit daily. Zero risk. Sign up today: http://elite-traders-wealth.com"),
    ("spam", "Get your high school diploma online in just 14 days! Accredited program. Enroll now: http://online-diploma-academy.net"),
    ("spam", "Your subscription to Mobile Games Club is active. You will be charged £4.99/week. To unsubscribe text STOP to 84433."),
    ("spam", "Congratulations! You won a pair of tickets to the Champions League Final. Call 0906-889-4433 to claim your tickets."),
    ("spam", "Free trial for premium anti-virus software. Protect your phone from hackers. Download now: http://mobile-security-scan.com"),
    ("spam", "Get cash back on your utility bills. Government scheme. Find out if you qualify: http://green-energy-grants.info"),
    ("spam", "Your FedEx tracking number 8837482 has a pending delivery. Action required: http://fedex-package-update.com"),
    ("spam", "Urgent response required: You have an outstanding tax refund of £348.10. Claim it online now: http://hmrc-tax-refund-claim.gov"),
    ("spam", "Get cheap loans with low interest rates. Instant approval. Apply today: http://easy-cash-loans.net"),
    ("spam", "Get 100 free tokens for online gaming. Click here to activate your account: http://free-token-promo.com"),
    ("spam", "Important security warning for your bank account. Update your security questions now: http://bank-security-update.com"),
    ("spam", "Congratulations! You have been selected for a £100 voucher from ASDA. Claim here: http://asda-voucher-draw.net"),
    ("spam", "Lose weight fast with our keto diet plan. 100% natural. Buy 1 get 1 free today: http://keto-diet-shop.com"),
    ("spam", "Urgent: Your PayPal payment of £238.50 to eBay was successful. If you did not make this purchase, call us immediately at 0800-443-9988.")
]


def load_dataset():
    """
    Tries to download the UCI SMS Spam Collection dataset.
    If it fails, loads the fallback dataset.
    Returns: X (list of texts), y (list of labels)
    """
    print("Attempting to download SMS Spam Collection dataset from UCI...")
    try:
        req = urllib.request.Request(
            DATASET_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            zip_file_bytes = response.read()
            
        with zipfile.ZipFile(io.BytesIO(zip_file_bytes)) as z:
            # The zip contains a file named 'SMSSpamCollection'
            with z.open('SMSSpamCollection') as f:
                content = f.read().decode('utf-8')
                
        texts = []
        labels = []
        for line in content.strip().split('\n'):
            parts = line.split('\t', 1)
            if len(parts) == 2:
                labels.append(parts[0].strip().lower())
                texts.append(parts[1].strip())
                
        print(f"Successfully loaded {len(texts)} samples from UCI dataset.")
        return texts, labels

    except Exception as e:
        print(f"Failed to download dataset: {e}")
        print("Falling back to local curated dataset...")
        labels = [item[0] for item in FALLBACK_DATA]
        texts = [item[1] for item in FALLBACK_DATA]
        print(f"Loaded {len(texts)} samples from fallback dataset.")
        return texts, labels


def train_and_save():
    texts, labels = load_dataset()
    
    # Train-test split
    # Since fallback dataset is small (120), if we use it, train_test_split might be small.
    # But it's okay for verifying metrics.
    test_size = 0.2 if len(texts) > 200 else 0.1
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=test_size, random_state=42, stratify=labels
    )
    
    # Create Pipeline elements
    # TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words='english',
        token_pattern=r'(?u)\b\w\w+\b' # standard word tokens
    )
    
    # Logistic Regression (gives calibrated probabilities)
    classifier = LogisticRegression(random_state=42, solver='liblinear')
    
    # Fit vectorizer
    X_train_vectorized = vectorizer.fit_transform(X_train)
    classifier.fit(X_train_vectorized, y_train)
    
    # Evaluate
    X_test_vectorized = vectorizer.transform(X_test)
    y_pred = classifier.predict(X_test_vectorized)
    
    print("\n--- Model Evaluation ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save combined pipeline as a dictionary/tuple
    pipeline = {
        'vectorizer': vectorizer,
        'classifier': classifier
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved successfully to: {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save()
