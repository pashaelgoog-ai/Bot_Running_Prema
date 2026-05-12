import telebot
import subprocess
import re
import os
import glob

# আপনার টেলিগ্রাম বট টোকেন
API_TOKEN = '8740604796:AAFSJtWED1QRajdvmaesiK5KsSogCoD0H9s'
bot = telebot.TeleBot(API_TOKEN)

user_sessions = {}

# সাইজ বের করার ফাংশন
def get_size(line):
    match = re.search(r'[0-9.]+(?:MiB|KiB|GiB|MB|KB|GB)', line)
    return match.group(0) if match else "N/A"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "লিংক দিন। অরিজিনাল টাইটেলসহ সেরা কোয়ালিটির MP3 এবং ভিডিও পাবেন।")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_link(message):
    url = message.text
    chat_id = message.chat.id
    bot.reply_to(message, "[~] স্ক্যান করা হচ্ছে, দয়া করে অপেক্ষা করুন...")

    try:
        # yt-dlp দিয়ে ফরম্যাট লিস্ট আনা
        cmd = f"yt-dlp --list-formats --no-warnings --no-check-certificate {url}"
        raw_data = subprocess.check_output(cmd, shell=True, text=True)
        
        format_map = {
            "0": "bestvideo+bestaudio/best",
            "mp3": "bestaudio/best"
        }
        
        final_msg = "🔹 [0] - Best Video (MP4)\n"
        final_msg += "🎵 [mp3] - Best Audio (MP3)\n\n"
        
        video_msg = "🎬 **Video Formats:**\n"
        audio_msg = "\n🎵 **Audio Formats:**\n"
        
        lines = raw_data.split('\n')
        i = 1
        for line in lines:
            if 'MiB' in line or 'GiB' in line or 'MB' in line:
                parts = line.split()
                f_id = parts[0]
                ext = parts[1]
                size = get_size(line)
                
                if 'audio only' in line:
                    audio_msg += f"{i}. {ext} | {size}\n"
                else:
                    res = parts[2] if len(parts) > 2 else "Video"
                    video_msg += f"{i}. {res} | {ext} | {size}\n"
                
                format_map[str(i)] = f_id
                i += 1
        
        user_sessions[chat_id] = {'url': url, 'map': format_map}
        bot.send_message(chat_id, final_msg + video_msg + audio_msg + "\nসিরিয়াল নম্বর বা 'mp3' লিখে পাঠান।")
        
    except Exception:
        bot.reply_to(message, "তথ্য পাওয়া যায়নি। লিংকটি সঠিক কিনা চেক করুন।")

@bot.message_handler(func=lambda message: True)
def handle_choice(message):
    chat_id = message.chat.id
    choice = message.text.lower()
    
    if chat_id in user_sessions:
        session = user_sessions[chat_id]
        url = session['url']
        
        if choice in session['map']:
            f_id = session['map'][choice]
            bot.send_message(chat_id, "📥 প্রসেসিং শুরু হয়েছে...")

            # অরিজিনাল টাইটেল ফেচ করা
            try:
                title = subprocess.check_output(f'yt-dlp --get-title "{url}"', shell=True, text=True).strip()
                # ফাইলের নামে সমস্যা করতে পারে এমন চিহ্ন রিমুভ করা
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_')]).rstrip()
            except:
                title = "Downloaded_File"
                safe_title = f"file_{chat_id}"

            # ডাউনলোড পাথ সেট করা
            # Termux এর জন্য /sdcard/Download/ ব্যবহার করতে পারেন, Colab এর জন্য /content/
            output_dir = "/sdcard/Download" if os.path.exists("/sdcard") else "."
            
            if choice == "mp3":
                dl_cmd = f'yt-dlp -f "{f_id}" --extract-audio --audio-format mp3 --audio-quality 0 "{url}" -o "{output_dir}/{safe_title}.mp3"'
            elif choice == "0":
                dl_cmd = f'yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 "{url}" -o "{output_dir}/{safe_title}.mp4"'
            else:
                # ভিডিও সিরিয়াল হলে অডিওসহ মার্জ করবে
                if any(x in f_id for x in ['140', '251', '249']): # অডিও আইডি চেক
                    dl_cmd = f'yt-dlp -f "{f_id}" "{url}" -o "{output_dir}/{safe_title}.%(ext)s"'
                else:
                    dl_cmd = f'yt-dlp -f "{f_id}+bestaudio/best" --merge-output-format mp4 "{url}" -o "{output_dir}/{safe_title}.mp4"'

            try:
                subprocess.run(dl_cmd, shell=True, check=True)
                
                # ফাইল খুঁজে পাঠানো
                files = glob.glob(f"{output_dir}/{safe_title}.*")
                if files:
                    target_file = files[0]
                    with open(target_file, 'rb') as f:
                        bot.send_document(chat_id, f, caption=f"✅ {title}")
                    os.remove(target_file) # মেমোরি বাঁচাতে ফাইল ডিলিট
                else:
                    bot.send_message(chat_id, "ফাইলটি তৈরি হতে সমস্যা হয়েছে।")
            except Exception as e:
                bot.send_message(chat_id, f"ডাউনলোড ব্যর্থ: {str(e)}")
    else:
        bot.reply_to(message, "আগে একটি লিংক দিন।")

print("বট সচল হয়েছে...")
bot.infinity_polling()
  
