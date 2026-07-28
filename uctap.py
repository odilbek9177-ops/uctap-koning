import random
import time
import json
import os
import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock

Window.clearcolor = (0.08, 0.08, 0.12, 1)

class CircleButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.2, 0.6, 0.9, 1)
            self.shape = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.update_shape, size=self.update_shape)

    def update_shape(self, *args):
        min_dim = min(self.width, self.height)
        x_offset = self.x + (self.width - min_dim) / 2
        y_offset = self.y + (self.height - min_dim) / 2
        self.shape.pos = (x_offset, y_offset)
        self.shape.size = (min_dim, min_dim)

class KoningClickerApp(App):
    def build(self):
        self.save_file = "koning_save.json"
        
        # Standart qiymatlar
        self.score = 0.0
        self.click_power = 1
        self.upgrade_level = 0
        self.last_spin_time = 0
        self.spin_cost = 2000
        self.last_save_time = time.time()
        
        # AUTO MINING (Passiv daromad: sekundiga 0.5 tanga)
        self.auto_mine_rate = 0.5
        
        # ENERGIYA TIZIMI QIYMATLARI (20,000 LIMIT)
        self.max_energy = 20000
        self.energy = 20000
        self.energy_upgrade_level = 0
        self.energy_rates = [1, 2, 4, 8, 15]  # Basish tezliklari
        self.energy_upgrade_costs = [7000, 14000, 21000, 28000]

        self.upgrade_costs = [1000, 5500, 11000, 20000, 35000]

        # Saqlangan ma'lumotlarni yuklash va oflayn daromadni hisoblash
        self.load_data()

        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        self.title_label = Label(text="[b]KONING CLICKER[/b]", markup=True, font_size='26sp', size_hint=(1, 0.07))
        self.score_label = Label(text=f"Tangalar: {int(self.score)}", font_size='22sp', size_hint=(1, 0.07))
        
        # Auto mine tezligini ko'rsatish
        self.auto_mine_label = Label(
            text=f"⚙️ Avto-mayning: +{self.auto_mine_rate}/s", 
            font_size='14sp', 
            color=(0.4, 0.9, 0.4, 1),
            size_hint=(1, 0.05)
        )

        main_layout.add_widget(self.title_label)
        main_layout.add_widget(self.score_label)
        main_layout.add_widget(self.auto_mine_label)

        # Kliklash tugmasi
        self.click_btn = CircleButton(
            text="[b]KONING[/b]\n(Bosing!)",
            markup=True,
            font_size='22sp',
            halign='center',
            size_hint=(1, 0.38)
        )
        self.click_btn.bind(on_press=self.on_click)
        main_layout.add_widget(self.click_btn)

        # ENERGIYA MATNI
        current_rate = self.energy_rates[self.energy_upgrade_level]
        self.energy_label = Label(
            text=f"⚡ Energiya: {int(self.energy)}/{self.max_energy} (+{current_rate}/s)", 
            font_size='16sp', 
            color=(0.2, 0.8, 1, 1),
            size_hint=(1, 0.06)
        )
        main_layout.add_widget(self.energy_label)

        # TUGBALAR PANELI
        bottom_layout = GridLayout(cols=2, spacing=8, size_hint=(1, 0.37))

        # 1. Click Upgrade tugmasi
        if self.upgrade_level >= len(self.upgrade_costs):
            upg_text = "[b]Click: MAX[/b]"
            upg_color = (0.5, 0.5, 0.5, 1)
        else:
            upg_text = f"Click (+1)\n{self.upgrade_costs[self.upgrade_level]} t"
            upg_color = (0.9, 0.5, 0.1, 1)

        self.upgrade_btn = Button(
            text=upg_text,
            font_size='11sp',
            background_color=upg_color,
            halign='center'
        )
        if self.upgrade_level >= len(self.upgrade_costs):
            self.upgrade_btn.markup = True
        self.upgrade_btn.bind(on_press=self.buy_upgrade)

        # 2. Energiya Tiklanishini Kuchaytirish tugmasi
        self.energy_upg_btn = Button(
            text="",
            font_size='11sp',
            background_color=(0.1, 0.6, 0.8, 1),
            halign='center'
        )
        self.update_energy_upgrade_btn_ui()
        self.energy_upg_btn.bind(on_press=self.buy_energy_upgrade)

        # 3. UC Yechish tugmasi
        self.uc_btn = Button(
            text="UC yechish",
            font_size='12sp',
            background_color=(0.1, 0.7, 0.3, 1),
            halign='center'
        )
        self.uc_btn.bind(on_press=self.open_uc_modal)

        # 4. Spin tugmasi
        self.spin_btn = Button(
            text=f"Spin\n({self.spin_cost} t)",
            font_size='12sp',
            background_color=(0.8, 0.2, 0.8, 1),
            halign='center'
        )
        self.spin_btn.bind(on_press=self.open_spin_modal)

        bottom_layout.add_widget(self.upgrade_btn)
        bottom_layout.add_widget(self.energy_upg_btn)
        bottom_layout.add_widget(self.uc_btn)
        bottom_layout.add_widget(self.spin_btn)

        main_layout.add_widget(bottom_layout)

        # O'yin davomida har 1 soniyada energiya va avto-mayningni yangilash
        Clock.schedule_interval(self.game_tick, 1.0)

        return main_layout

    # HAR SEKUNDLIK O'YIN TIK-TIK HODISASI (ENERGIYA + AVTO-MAYNING)
    def game_tick(self, dt):
        # 1. Avto-mayning (Sekundiga +0.5 tanga)
        self.score += self.auto_mine_rate
        self.score_label.text = f"Tangalar: {int(self.score)}"

        # 2. Energiya tiklanishi
        rate = self.energy_rates[self.energy_upgrade_level]
        if self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + rate)
            self.energy_label.text = f"⚡ Energiya: {int(self.energy)}/{self.max_energy} (+{rate}/s)"
            
        self.save_data()

    # CLICK HODISASI
    def on_click(self, instance):
        if self.energy >= self.click_power:
            self.energy -= self.click_power
            self.score += self.click_power
            self.score_label.text = f"Tangalar: {int(self.score)}"
            
            rate = self.energy_rates[self.energy_upgrade_level]
            self.energy_label.text = f"⚡ Energiya: {int(self.energy)}/{self.max_energy} (+{rate}/s)"
            self.save_data()
        else:
            rate = self.energy_rates[self.energy_upgrade_level]
            self.energy_label.text = f"⚡ ENERGIYA YETARLI EMAS! ({int(self.energy)}/{self.max_energy})"

    # ENERGIYA UPGRADE XARIDI
    def buy_energy_upgrade(self, instance):
        if self.energy_upgrade_level >= len(self.energy_upgrade_costs):
            return

        cost = self.energy_upgrade_costs[self.energy_upgrade_level]

        if self.score >= cost:
            self.score -= cost
            self.energy_upgrade_level += 1
            self.score_label.text = f"Tangalar: {int(self.score)}"
            
            rate = self.energy_rates[self.energy_upgrade_level]
            self.energy_label.text = f"⚡ Energiya: {int(self.energy)}/{self.max_energy} (+{rate}/s)"
            
            self.update_energy_upgrade_btn_ui()
            self.save_data()
        else:
            self.show_alert("Xatolik", f"Tangalaringiz yetarli emas!\nYana {int(cost - self.score)} tanga kerak.")

    def update_energy_upgrade_btn_ui(self):
        if self.energy_upgrade_level >= len(self.energy_upgrade_costs):
            self.energy_upg_btn.text = "[b]Recharge: MAX[/b]"
            self.energy_upg_btn.markup = True
            self.energy_upg_btn.background_color = (0.5, 0.5, 0.5, 1)
        else:
            cost = self.energy_upgrade_costs[self.energy_upgrade_level]
            next_rate = self.energy_rates[self.energy_upgrade_level + 1]
            self.energy_upg_btn.text = f"Tiklanish (+{next_rate}/s)\n{cost} t"

    # SAQLASH VA YUKLASH (OFLAYN DAROMAD VA ENERGIYANI HISOBLASH)
    def save_data(self):
        data = {
            "score": self.score,
            "click_power": self.click_power,
            "upgrade_level": self.upgrade_level,
            "last_spin_time": self.last_spin_time,
            "energy": self.energy,
            "energy_upgrade_level": self.energy_upgrade_level,
            "last_save_time": time.time()  # Chiqib ketilgan vaqt
        }
        try:
            with open(self.save_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print("Saqlashda xatolik:", e)

    def load_data(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    data = json.load(f)
                    self.score = data.get("score", 0.0)
                    self.click_power = data.get("click_power", 1)
                    self.upgrade_level = data.get("upgrade_level", 0)
                    self.last_spin_time = data.get("last_spin_time", 0)
                    self.energy = data.get("energy", 20000)
                    self.energy_upgrade_level = data.get("energy_upgrade_level", 0)
                    
                    last_save = data.get("last_save_time", time.time())
                    current_time = time.time()
                    elapsed_seconds = max(0, current_time - last_save)

                    # OFLAYN ISHLANGAN TANGALAR
                    offline_earned = elapsed_seconds * self.auto_mine_rate
                    self.score += offline_earned

                    # OFLAYN TIKLANGAN ENERGIYA
                    rate = self.energy_rates[self.energy_upgrade_level]
                    offline_energy = elapsed_seconds * rate
                    self.energy = min(self.max_energy, self.energy + offline_energy)

            except Exception as e:
                print("Yuklashda xatolik:", e)

    def buy_upgrade(self, instance):
        if self.upgrade_level >= len(self.upgrade_costs):
            return

        cost = self.upgrade_costs[self.upgrade_level]

        if self.score >= cost:
            self.score -= cost
            self.upgrade_level += 1

            if self.upgrade_level == 5:
                self.click_power = 8
            else:
                self.click_power += 1

            self.score_label.text = f"Tangalar: {int(self.score)}"

            if self.upgrade_level >= len(self.upgrade_costs):
                self.upgrade_btn.text = "[b]Click: MAX[/b]"
                self.upgrade_btn.markup = True
                self.upgrade_btn.background_color = (0.5, 0.5, 0.5, 1)
            else:
                next_cost = self.upgrade_costs[self.upgrade_level]
                self.upgrade_btn.text = f"Click (+1)\n{next_cost} t"

            self.save_data()
        else:
            self.show_alert("Xatolik", f"Tangalaringiz yetarli emas!\nYana {int(cost - self.score)} tanga kerak.")

    # SPIN BO'LIMI
    def open_spin_modal(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)

        info_label = Label(
            text="[b]OMAD G'ILDIRAGI[/b] (Kuniga 1 marta)\n\n• 2x 5,000 tanga (49.8%)\n• 2x 10,000 tanga (49.8%)\n• 2x 17,000 tanga (0.4% JackPot!)",
            markup=True,
            halign='center',
            font_size='14sp'
        )
        content.add_widget(info_label)

        self.spin_result_label = Label(
            text="Aylantirish uchun tugmani bosing!",
            font_size='14sp',
            color=(0.2, 0.8, 0.2, 1),
            halign='center'
        )
        content.add_widget(self.spin_result_label)

        action_btn = Button(
            text=f"Aylantirish ({self.spin_cost} tanga)",
            size_hint=(1, 0.25),
            background_color=(0.8, 0.2, 0.8, 1)
        )
        action_btn.bind(on_press=self.do_spin)
        content.add_widget(action_btn)

        close_btn = Button(text="Yopish", size_hint=(1, 0.2), background_color=(0.8, 0.2, 0.2, 1))
        content.add_widget(close_btn)

        self.spin_popup = Popup(title="Spin", content=content, size_hint=(0.85, 0.6), auto_dismiss=False)
        close_btn.bind(on_press=self.spin_popup.dismiss)
        self.spin_popup.open()

    def do_spin(self, instance):
        current_time = time.time()
        cooldown = 24 * 3600  # 24 soat

        if current_time - self.last_spin_time < cooldown:
            remaining = cooldown - (current_time - self.last_spin_time)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            self.spin_result_label.text = f"Kunlik limitga yetdingiz!\nKeyingi spin: {hours}s {minutes}daq dan so'ng"
            self.spin_result_label.color = (0.9, 0.2, 0.2, 1)
            return

        if self.score < self.spin_cost:
            self.spin_result_label.text = "Tangalar yetarli emas!"
            self.spin_result_label.color = (0.9, 0.2, 0.2, 1)
            return

        self.score -= self.spin_cost
        self.last_spin_time = current_time

        options = [17000, 5000, 10000]
        weights = [0.4, 49.8, 49.8]

        won_amount = random.choices(options, weights=weights, k=1)[0]
        self.score += won_amount
        self.score_label.text = f"Tangalar: {int(self.score)}"

        if won_amount == 17000:
            self.spin_result_label.text = f"SUPER YUTUQ! 🎉 17,000 tanga!"
            self.spin_result_label.color = (1, 0.8, 0, 1)
        else:
            self.spin_result_label.text = f"Siz {won_amount} tanga yutdingiz!"
            self.spin_result_label.color = (0.2, 0.8, 0.2, 1)

        self.save_data()

    # UC DO'KONI VA TELEGRAM INTEGRATSIYASI
    def open_uc_modal(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        grid = GridLayout(cols=2, spacing=10, size_hint=(1, 0.85))

        uc_packages = [
            (50000, 60),
            (98899, 120),
            (147899, 180),
            (299299, 325)
        ]

        for price, uc in uc_packages:
            btn = Button(
                text=f"[b]{uc} UC[/b]\n\n{price:,} tanga".replace(',', ' '),
                markup=True,
                font_size='13sp',
                background_color=(0.2, 0.4, 0.8, 1),
                halign='center'
            )
            btn.bind(on_press=lambda inst, p=price, u=uc: self.check_before_id_prompt(p, u))
            grid.add_widget(btn)

        content.add_widget(grid)

        close_btn = Button(text="Yopish", size_hint=(1, 0.15), background_color=(0.8, 0.2, 0.2, 1))
        content.add_widget(close_btn)

        self.uc_popup = Popup(title="UC Do'koni", content=content, size_hint=(0.9, 0.65), auto_dismiss=False)
        close_btn.bind(on_press=self.uc_popup.dismiss)
        self.uc_popup.open()

    def check_before_id_prompt(self, price, uc):
        if self.score >= price:
            self.uc_popup.dismiss()
            self.open_id_prompt(price, uc)
        else:
            self.show_alert("Xatolik", f"Tangalaringiz yetarli emas!\nYana {int(price - self.score)} tanga kerak.")

    def open_id_prompt(self, price, uc):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(text=f"{uc} UC yechib olish uchun\nPUBG ID raqamingizni kiriting:", halign='center'))
        
        id_input = TextInput(
            hint_text="Masalan: 52102259303",
            multiline=False,
            input_filter='int',
            size_hint=(1, 0.4),
            font_size='16sp'
        )
        content.add_widget(id_input)

        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.4))
        submit_btn = Button(text="Yechish", background_color=(0.1, 0.7, 0.3, 1))
        cancel_btn = Button(text="Bekor qilish", background_color=(0.8, 0.2, 0.2, 1))

        btn_layout.add_widget(submit_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        id_popup = Popup(title="PUBG ID Kiriting", content=content, size_hint=(0.85, 0.45), auto_dismiss=False)

        submit_btn.bind(on_press=lambda inst: self.finalize_uc_buy(price, uc, id_input.text, id_popup))
        cancel_btn.bind(on_press=id_popup.dismiss)

        id_popup.open()

    def finalize_uc_buy(self, price, uc, user_id, popup):
        if not user_id.strip():
            self.show_alert("Xatolik", "Iltimos, PUBG ID raqamingizni kiriting!")
            return

        self.score -= price
        self.score_label.text = f"Tangalar: {int(self.score)}"
        self.save_data()
        popup.dismiss()

        msg = f"Salom! Men KONING Clicker o'yinidan {uc} UC yechib olmoqchiman. PUBG ID: {user_id}"
        telegram_url = f"https://t.me/koning_uc?text={msg.replace(' ', '%20')}"
        
        webbrowser.open(telegram_url)

        self.show_alert("Qabul qilindi!", f"ID: {user_id}\n\n{uc} UC uchun Telegram arizangiz tayyorlandi!")

    def show_alert(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, halign='center'))
        ok_btn = Button(text="OK", size_hint=(1, 0.3))
        content.add_widget(ok_btn)
        
        alert = Popup(title=title, content=content, size_hint=(0.8, 0.35))
        ok_btn.bind(on_press=alert.dismiss)
        alert.open()

if __name__ == '__main__':
    KoningClickerApp().run()
