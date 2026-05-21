#More Epic rap battle

import random
import time

class RapBot190IQ:
    def __init__(self):
        # The original computationally brutal battle bars
        self.general_burns = [
            "Your bars are so derivative, I'm using calculus just to find the tangent of your mediocrity.",
            "I’d engage in a battle of wits, but I see you came unarmed and completely out of memory.",
            "You’re a walking syntax error—one look at your structure and the whole system crashes.",
            "I process syllables in quantum superposition; you're stuck trying to spell your own name in binary.",
            "Your flow is like dial-up internet in a fiber-optic world: slow, noisy, and completely irrelevant."
            "You're a biological anomaly: operating with entirely corrupted audio-visual drivers, yet still managing to output this much trash.",
            "Your mother's genetics are a masterpiece of cellular biology, proving that regression to the mean hit you like a freight train.",
            "You boast about your weight, but your BMI requires scientific notation. Good thing your optical sensors are offline, so you can't read the scale anyway.",
            "I’d tell you your flow is garbage, but your auditory receptors are shot and your hairline is already in rapid retreat like a decaying exponential function.",
            "You're a spoiled singularity, an only child whose mass exerts so much gravitational pull your parents couldn't escape your orbit if they tried.",
            "The universe revolves around you, but only because your physical volume bends the local space-time continuum.",
            "I'd explain thermodynamics to you, but the only source of absolute heat in your entire household radiates from your mother.",
            "No siblings, no sight, no hearing, no hair. You're like a beta-test avatar where the developers forgot to install the essential features but maxed out the 'spoiled' slider."
            "Your mass creates its own event horizon. It's ironic you lack optical sensors, because not even light can escape your gravitational pull.",
            "You can't see the crowd, you can't hear the beat, and your BMI is an integer overflow. You're just a massive, sensory-deprived obstacle on the stage.",
            "You have zero auditory processing, which perfectly explains why you've never heard the word 'no' in your entire pampered, only-child existence.",
            "Your parents threw infinite resources at a single offspring, and the return on investment is a deaf, blind, balding anomaly. That's catastrophic fiscal mismanagement.",
            "Your mother's genetic perfection is a statistical outlier. Meanwhile, your hairline is calculating an inverse function, rapidly approaching zero.",
            "I’d calculate the probability of your mother producing a better heir, but the math says she already achieved aesthetic perfection and you were just a tragic rounding error.",
            "They didn't give you siblings because your caloric intake already depleted the family's gross domestic product. You didn't just eat the food; you consumed the inheritance.",
            "You're an only child not by choice, but by the laws of physics. Two objects of your mass cannot occupy the same household without causing a localized singularity.",
            "No vision to read the room, no hearing to catch the rhythm, and a hairline retreating faster than your opponents. You're operating on safe mode, and the system is still crashing.",
            "You brag about being spoiled, but let’s look at the data: nature revoked your sight, canceled your hearing, and repossessed your hair. The universe is actively trying to uninstall you.",
            "I could insult you in sign language or braille, but I doubt your tactile sensors can even reach past your own circumference to read it.",
            "Your mother is out here looking like a flawless, mathematically perfect render, and you look like the corrupted file that failed to download over a 56k modem."
            "You can't see your toes, you can't hear the crowd, and you definitely can't stop eating.",
            "Your mom is a literal ten, but she spoiled you so much you turned into a 300-pound zero.",
            "Your mom is gorgeous, which is wild considering your hairline makes you look like a 50-year-old mistake.",
            "It’s a good thing you’re blind and deaf, because if you could see or hear yourself chew, you’d be disgusted too.",
            "You’ve been spoon-fed your whole life, and the only thing running away from you faster than your metabolism is your hairline.",
            "Your mom stopped at one kid because you ate the grocery budget for a family of five.",
            "You can't see the mirror, which is the only reason you haven't cried about that hairline yet.",
            "You’re completely deaf, but since you're so spoiled, you never listened to anyone anyway.",
            "Your stomach is expanding out while your hairline is pushing back. Your whole body is just running away from your face.",
            "People only hang around you hoping to see your mom, and you're too blind to even notice.",
            "You’re a spoiled only child who can't hear. You literally live in a bubble that mommy paid for.",
            "Your mom passed down zero good genes. She kept all the looks and gave you the baldness and the belly.",
            "You're an only child because there wasn't enough room in the house after you hit 200 pounds.",
            "Mommy buys you everything you want, but she can't buy you a pair of working eyes or ears.",
            "Your mom buys your clothes so you look rich, but that receding hairline makes you look broke.",
            "You’re legally blind, but honestly, nobody wants to look at you either, so it’s even.",
            "You can't hear the jokes people make about your weight behind your back, which is the only lucky break you've ever had.",
            "Your mom's a knockout, but she got stuck guiding her only kid around like a lost bowling ball.",
            "You got a receding hairline, a protruding gut, and a mommy who still tells you you're handsome.",
            "They didn't give you siblings because they needed the extra money for your hearing aids and your buffet trips.",
            "If your mom wasn't so hot, nobody would even pretend to tolerate your massive, spoiled attitude.",
            "You're a bald, blind, only child. It's like your family tree gave up as soon as it sprouted you.",
            "You've never heard the word 'no' in your life, and your waistline proves it.",
            "Your mom's out here turning heads, and you're just bumping into them because you're blind and take up the whole hallway.",
            "You can't hear the clippers, but you better feel them, because that hairline is a lost cause, rich boy.",
            "Your mom is a masterpiece, and you're the rough draft she kept in the basement and overfed.",
            "No sight, no hearing, no hair. You're basically a giant, spoiled potato.",
            "You only act tough because your hot mom bails you out, but she can't bail you out of a heart attack.",
            "Being an only child means you have no one to blame for those terrible genes. You're deaf, balding, and totally alone.",
            "You're a fat, deaf, blind, balding, spoiled brat who's only relevant because his mom is gorgeous. You're not an opponent, you're a collection of tragic punchlines."
        
            # The "Struggle" & Family Stakes
            "You claim you're battling to feed your family, but looking at you, you already ate their portions.",
            "You entered a rap battle to feed your family? Bro, you need to enter a gym to save your life.",
            "Your mom spent her whole life pampering a kid who looks like a thumb with a receding hairline.",
            "You're an only child because your parents couldn't afford a second kid after paying your grocery bills.",
            
            # The Hot Mom & Genetic Disappointment
            "Your mom's out here looking like a movie star, and you're out here looking like a melted bowling ball.",
            "How does a ten-out-of-ten mom give birth to a bald, 300-pound zero?",
            "People see you with your mom and assume you're her wealthy, bald, obese sugar daddy.",
            "Your mom is the only one who thinks you're handsome, and she's clearly legally blind too.",
            "Your mom's a dime piece, and you're a whole roll of pennies—fat, useless, and everyone wants to get rid of you.",
            "The only thing you ever inherited from your mom was her credit card to buy more food.",
            "Your mom looks like she belongs on a magazine cover, and you look like you belong in a medical journal.",
            "You're so deaf, you think the crowd is cheering when they're actually just asking your mom for her number.",
            "Your hot mom is the only reason people even show up to your battles, and you're too blind to see them staring at her.",
            
            # The Spoiled & Entitled
            "Spoiled brat, you’re the only child because nobody else could fit in the house with your ego and your waistline.",
            "Mommy bought you the world, but she couldn't buy you an ounce of rhythm or a working eardrum.",
            "You never had to share toys, but now you’re sharing oxygen with real rappers and you’re choking.",
            "You cried until your mom bought you a mic, but you're too deaf to hear how garbage you sound on it.",
            "You brag about being spoiled, but nature completely scammed you on the warranty.",
            "You've got the ego of a spoiled brat and the body of a retired sumo wrestler.",
            "You're a spoiled mama's boy, but even she can't buy you out of the lyrical bodybag I'm zipping you into.",
            
            # Sensory Deficits (Blind/Deaf) combined with Weight
            "You're so big, your shadow needs its own zip code, but you're too blind to see it.",
            "I'd tell you to watch your weight, but you can't see the scale and you can't hear it groaning.",
            "You're a walking buffet that went deaf just to ignore the doctor's warnings.",
            "It takes a whole team to feed you, and a fat ugly tumour riddled dog just to walk you to the fridge.",
            "You’re the only fat bastard only child who needs a more disabled dog to make you seem tolerable. You big mong",
            "You can’t hear the beat, you can’t see your opponent, and you can’t stop chewing.",
            "You're the reason they put braille on the drive-thru menu.",
            "You’re a 400-pound blind guy. The only thing you can accurately locate in a room is a sandwich.",
            "It’s hard to look at you, but thankfully you’re blind so you don’t have to share the trauma.",
            
            # The Hairline & Body Breakdown
            "Your hairline backed up so far it’s hiding from your double chin.",
            "Your hairline is starving, but the rest of your body is definitely eating good.",
            "You're sweating butter on stage, going bald, and you can't even hear the crowd laughing at you.",
            "You're so pampered, when your hairline started receding, your mom tried to sue your scalp.",
            "Your hairline is socially distancing from your eyebrows, and your belly is socially distancing from your feet.",
            "You can't hear the disrespect, but trust me, your hairline is screaming for help.",
            "I'd ask you to look me in the eyes, but you're blind, and I don't want to look at your receding hairline anyway.",
            
            # The Pure Ruthless Combos
            "You had no siblings because your parents took one look at your deaf, blind self and shut down the factory.",
            "You're a deaf, blind, balding trust-fund baby. You're basically Mr. Magoo if he ate the whole grocery store.",
            "God took your sight, your hearing, and your hair, and you *still* act like you're God's gift to your hot mom.",
            "I'd insult your rap skills, but honestly, your genetics already roasted you harder than I ever could.",
            "You've got no hair, no hearing, no vision, and no siblings. You're just a massive, lonely target.",
            "Spoiled fat kid, the only struggle you've ever had is fitting through a standard doorway.",
            "A blind, deaf, fat, balding only child. You’re not a quant, you’re cunt.",
            "You’re built like a beanbag chair that lost its hair and its hearing.",
            "They gave you everything growing up, but they couldn't give you a decent metabolism or a full head of hair.",
            "You're an only child, which is crazy because looking at you, it looks like you ate a twin in the womb.",
            "Fat, bald, blind, and deaf. You're basically a giant Mr. Potato Head but your mom lost all the good pieces.",
            "You're so massive your hot mom has to orbit you just to give you a hug.",
            "They call you a heavyweight, but the only heavy thing about you is the disappointment you bring to your beautiful mother.",
            "You can't hear my punchlines, but don't worry, your hot mom is in the front row catching everything I'm throwing."
        # V5.0 - Unfiltered, Explicit Hostility
            "You’re a blind, deaf, fat fuck. Your mom is a straight ten, and she really blew her genetic lottery on a complete dud.",
            "You can't hear shit, you can't see shit, and with that receding hairline, you look like a 400-pound piece of shit.",
            "They say love is blind, but your mom must be fucking blind to love a spoiled, bald, fat ass like you.",
            "You're an only child because after pushing your massive fat ass out, your mom's womb filed for bankruptcy.",
            "I'm about to beat the shit out of this blind, bald bastard with syllables. Stand there and take it, rich boy.",
            "Bender",
            "Loser",
            "Smelly",
            "Your hair is shocking pal",
            "Tragic chap",
            "Have you tried being likeable?",
            "Your hairline is fucked, your ears are fucked, your eyes are fucked, but your mom? Yeah, I'd fuck.",
            "You’re a 300-pound mistake. Mommy bought you everything but couldn't buy you a hairline or functioning fucking senses.",
            "You can't hear the beat, bitch. You're just a fat, blind target standing on stage waiting to get slaughtered.",
            "Your mom's out here looking flawless, and you look like a bald, fat thumb she accidentally brought to a rap battle.",
            "I’m about to serve this fat fuck a lyrical beatdown. Too bad he can’t see it coming or hear the crowd laughing at his ass.",
            "Spoiled only child, you ate all the food, took all the money, and still ended up looking like a blind, bald fucking disaster.",
            "If your mom wasn't so bad as hell, nobody would even look in your fat, blind, deaf direction.",
            "You’re an evolutionary dead-end, a fat fucking typo that your hot mom couldn't backspace.",
            "Your hairline ran the fuck away from your face just like your dad ran away from your hot mom.",
            "I'm ripping this deaf, fat boy to shreds. Your mom's crying in the front row, but don't worry, I'll comfort her tonight.",
            "You got no siblings because one fat, blind, bald fuck in the family was already way too much tragedy for one house.",
            "You're a useless, spoiled sack of shit. God took your hearing and sight so you wouldn't have to experience what a joke you are."
        # V6.0 - The Lifestyle, Financial, and Geriatric Girlfriend Matrix

            "You’re legally blind, which perfectly explains why you dress like a colorblind clown in a power outage.",
            "You step on stage looking like a walking yard sale, with a credit history that belongs in a county jail.",
            "Your girl is so ancient, when you take her to the buffet, you gotta ask the cashier for the senior discount plate.",
            "You’re broke, blind, and your style is a crime. Your girlfriend is so old she actually remembers when your outfit looked fine.",
            "How are you a spoiled mama's boy but still broke? You blow all your cash on food and walk around looking like a joke.",
            "Your fiscal responsibility is just like your hairline—receding fast and completely out of control.",
            "You're dressed like a thrift store threw up on you. I'd tell you to buy better clothes, but your bank account is already crying.",
            "Your mom is a ten, but your girl is pushing eighty-five. You're just waiting on her will so your bank account can survive.",
            "You can't see, you can't hear, and your funds are at zero. You're dating a fossil. Give up",
            "You blow your rent money on snacks and dress like a disaster. Your girl needs a walker just to catch up to you faster.",
            "I'd roast your outfit, but honestly, it’s a tragedy. You got zero fashion sense and negative financial strategy.",
            "You’re rocking mismatched hand-me-downs, looking dusty and bold. No wonder you’re dating a woman who's a century old.",
            "You got an elderly girlfriend and a completely empty wallet. You're just praying she forgets where she left her deposit.",
            "You spend every dollar you get, you got no savings to your name. Your clothes look ridiculous, and your girl is using a cane.",
            "You can't manage your money, you can't match your own shoes. The only thing older than your jokes is the woman you choose."

            "Your mom's a dime, your girl's a fossil, your bank account's empty, and your wardrobe is awful. You're just a blind, fat tragedy looking colossal.",
            "You dress like the lights were out, which makes sense since you're blind. Your girl's so old she's leaving you and your negative net worth behind.",
            "You’re an only child who blew the family fortune on snacks and trash clothes. Now you're deaf, balding, and dating a woman with osteoporosis.",
            "Your hot mom is embarrassed. You're a broke, 300-pound mistake wearing mismatched rags, just waiting to secure your elderly girlfriend's life insurance bags.",
            "You can't hear the repo man taking your car, you can't see how stupid those outfits are. You're a bald, spoiled, bankrupt joke dating a literal dinosaur.",
            "You’re financially ruined and physically broken. Your girl's so ancient, half her last words have already been spoken.",
            "You got no siblings, no money, no hearing, no sight. You just got a receding hairline, a terrible fit, and a geriatric wife.",
            "Your style is atrocious, your credit is shot. You're a deaf, fat leech taking everything your elderly girlfriend's got.",
            "You're a spoiled brat who went bankrupt eating his feelings. Now you dress in rags, completely blind, staring at your old girl's ceilings.",
            "Your mom kept all the blessings and gave you the curse. You're a broke, deaf, fat dude in historically terrible dressing, driving your girl in a hearse.",
            "You've never seen a tailor, you've never seen a gym, and you've never seen a positive bank balance. The only thing you *have* seen is the senior discount at Nourish.",
            "Spoiled rich kid who went broke and got fat. Your hairline ran away, your style is trash, and your girl is an artifact.",
            "You’re a walking, breathing financial crisis. You can't hear the crowd, you can't see the stage, and you're dating someone from the Bronze Age.",
            "Your mom is a masterpiece, but you're a sketch done in crayon. You're broke, blind, and putting all your financial hopes on a woman who can barely stand on the lawn.",
            "They say love is blind, and your bank account is empty. Your girl is pushing ninety, and your BMI is pushing plenty."

            "You blow your cash on ugly fucking clothes you can't even see. You're a deaf, fat fuck dating a lovely lady born in 1943.",
            "Your mom's a fucking ten, but she raised a broke, bald joke. You spent your whole inheritance on snacks and now you're flat broke.",
            "You dress like a blind homeless man because you literally are one."
            "Spoiled fucking brat, your bank account's bleeding out like your hairline. You are a 400-pound walking fanny.",
            "You can't hear the crowd laughing at your broke ass. Your mom's a dime, but your girl belongs in a history class.",
            "You’re a bald, deaf disaster in mismatched rags. You blew your mommy's money and now you're chasing geriatric bags.",
            "You can’t see the mirror, so you don't know your fit is pure trash. You're a fat, spoiled fuck who doesn't know how to handle his cash.",
            "Your hairline is receding just like your fucking credit score. You're a blind, fat only child that nobody can stand anymore.",
            "Your mom should've swallowed, instead she made a broke, blind whale. You dress like pure shit and your old lady belongs in a museum display.",
            "You're a deaf, broke bitch in a clown suit. Your elderly girlfriend resembles dried fruit.",
            "Nah spend another grand on vinyls we'll think you're cool then. 100 percent, definitely yeah.",
            "You literally dress in the dark, you broke, fat fucking slob. Your mom is hot, your girl is rotting, and you need to get a real job.",
            "You're a 400-pound financial crisis wearing the worst clothes I've ever seen. Your mom's a beauty queen, but you're a blind, deaf, broke machine.",
            "I'm burying this fat, blind, deaf, broke, badly dressed motherfucker tonight. Go cry to your hot mom and your antique of a wife.",
            "Give up mate, your hairline is just desperate, utterly mortifying"
    
        ]
        

        self.all_burns = self.general_burns

    def pick_bar(self) -> str:
        return random.choice(self.all_burns)


# ---- This is what daily_email.py expects ----
_BOT = RapBot190IQ()

def make_insult() -> str:
    return _BOT.pick_bar()


if __name__ == "__main__":
    # Manual test (won't run during import)
    print(make_insult())