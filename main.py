"""AutoScout Mobile — phone-first Kivy interface using the AutoScout 4.1.0 engine."""
from __future__ import annotations
import json, os, threading, webbrowser
from functools import partial
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
import autoscout_core as core

MAROON = (0.365, 0.031, 0.122, 1)   # #5d081f
PAGE = (0.933, 0.945, 0.965, 1)     # #eef1f6
WHITE = (1, 1, 1, 1)
INK = (0.094, 0.133, 0.212, 1)      # #182236
MUTED = (0.42, 0.45, 0.50, 1)
BORDER = (0.89, 0.91, 0.93, 1)
RED = (0.78, 0.16, 0.20, 1)
RED_LIGHT = (1.00, 0.91, 0.91, 1)
BLUE = (0.12, 0.35, 0.76, 1)
BLUE_LIGHT = (0.90, 0.94, 1.00, 1)
SELECTED = (1.00, 0.91, 0.55, 1)
SELECTED_LIGHT = (1.00, 0.97, 0.84, 1)

class Card(BoxLayout):
    def __init__(self, **kw):
        # Defaults remain overridable by individual cards without duplicate kwargs.
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', dp(12))
        kw.setdefault('spacing', dp(8))
        kw.setdefault('size_hint_y', None)
        super().__init__(**kw)
        self.bind(minimum_height=self.setter('height'))
        with self.canvas.before:
            Color(*WHITE)
            self.bg = RoundedRectangle(radius=[dp(13)])
        self.bind(pos=self._paint, size=self._paint)
    def _paint(self,*_): self.bg.pos=self.pos; self.bg.size=self.size

class BarTrack(BoxLayout):
    """Responsive horizontal metric bar used by the real grouped team chart."""
    def __init__(self, label_text, value, maximum, color, **kw):
        super().__init__(orientation='horizontal', spacing=dp(6), size_hint_y=None, height=dp(19), **kw)
        self.add_widget(Label(text=label_text, size_hint_x=None, width=dp(34), font_size=sp(10), color=MUTED, halign='left', valign='middle'))
        self.track = Widget()
        with self.track.canvas:
            Color(0.92, 0.93, 0.95, 1)
            self.track_bg = RoundedRectangle(radius=[dp(4)])
            Color(*color)
            self.track_fg = RoundedRectangle(radius=[dp(4)])
        self.track.bind(pos=self._draw, size=self._draw)
        self.add_widget(self.track)
        self.add_widget(Label(text=f'{value:.1f}', size_hint_x=None, width=dp(43), font_size=sp(10), color=INK, halign='right', valign='middle'))
        self.value = max(0.0, float(value)); self.maximum = max(1.0, float(maximum))
    def _draw(self, *_):
        w=max(0,self.track.width); h=max(0,self.track.height)
        self.track_bg.pos=self.track.pos; self.track_bg.size=(w,h)
        self.track_fg.pos=self.track.pos; self.track_fg.size=(w*min(1,self.value/self.maximum),h)

class LineChart(Widget):
    """Simple responsive plotted line chart drawn with Kivy canvas primitives."""
    def __init__(self, values, **kw):
        super().__init__(size_hint_y=None, height=dp(220), **kw)
        self.values=list(values)
        self.bind(pos=self._draw_chart, size=self._draw_chart)
        self._draw_chart()
    def _draw_chart(self, *_):
        self.canvas.clear()
        if len(self.values)<2:return
        xs=[float(p[0]) for p in self.values]; ys=[float(p[1]) for p in self.values]
        xmin,xmax=min(xs),max(xs); ymin=0.0; ymax=100.0
        left=self.x+dp(38); right=self.right-dp(12); bottom=self.y+dp(28); top=self.top-dp(12)
        width=max(1,right-left); height=max(1,top-bottom)
        with self.canvas:
            # Horizontal grid and axes
            for pct in (0,25,50,75,100):
                y=bottom+height*pct/100
                Color(0.86,0.88,0.91,1)
                Line(points=[left,y,right,y],width=1)
            Color(0.35,0.39,0.46,1)
            Line(points=[left,bottom,left,top],width=1.2)
            Line(points=[left,bottom,right,bottom],width=1.2)
            points=[]
            for x,y in self.values:
                px=left+(float(x)-xmin)/(xmax-xmin or 1)*width
                py=bottom+(float(y)-ymin)/(ymax-ymin)*height
                points.extend([px,py])
            Color(*MAROON)
            Line(points=points,width=2.4)
            Color(*BLUE)
            for i in range(0,len(points),2):
                from kivy.graphics import Ellipse
                Ellipse(pos=(points[i]-dp(3),points[i+1]-dp(3)),size=(dp(6),dp(6)))

class AutoScoutMobile(App):
    title = 'FTC AutoScout'
    def build(self):
        Window.clearcolor = PAGE
        self.session = core.Session(season=2026)
        self.client = core.FTCScoutClient(cache_dir=self.user_data_dir)
        self.page = 'Home'
        self.selected_team = int(self.session.my_team or 0)
        self.scouts = []
        self.watch_teams = []
        self.assignments = {}
        self._load_mobile_state()
        self.selected_team = int(self.session.my_team or 0)
        self.root_box = BoxLayout(orientation='vertical', spacing=0)
        self.header = BoxLayout(size_hint_y=None, height=dp(66), padding=[dp(14),dp(8)], spacing=dp(10))
        with self.header.canvas.before:
            Color(*MAROON); self.header_bg=RoundedRectangle()
        self.header.bind(pos=self._header_paint,size=self._header_paint)
        logo=os.path.join(os.path.dirname(__file__),'assets','AutoScout_Logo_56.png')
        if os.path.exists(logo): self.header.add_widget(Image(source=logo,size_hint=(None,None),size=(dp(46),dp(46)),allow_stretch=True))
        self.menu_button=Button(text='MENU',size_hint=(None,None),size=(dp(54),dp(42)),background_normal='',background_color=(0.48,0.10,0.19,1),color=WHITE,font_size=sp(11),bold=True)
        self.menu_button.bind(on_release=self.open_menu)
        self.header.add_widget(self.menu_button)
        titlebox=BoxLayout(orientation='vertical',spacing=0)
        titlebox.add_widget(Label(text='FTC AutoScout',bold=True,font_size=sp(20),color=WHITE,halign='left',valign='bottom'))
        titlebox.add_widget(Label(text='SCOUTING MADE EASY',font_size=sp(9),color=(0.86,0.86,0.88,1),halign='left',valign='top'))
        self.header.add_widget(titlebox)
        self.header.add_widget(Widget())
        self.root_box.add_widget(self.header)
        # Compact loading/progress strip replaces the old horizontal navigation row.
        self.progress_box=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(42),padding=[dp(12),dp(4)],spacing=dp(2),opacity=0,disabled=True)
        self.progress_label=Label(text='Ready',font_size=sp(10),color=MUTED,halign='left',valign='middle',size_hint_y=None,height=dp(16))
        self.progress_label.bind(size=lambda o,v:setattr(o,'text_size',(v[0],None)))
        self.progress_bar=ProgressBar(max=100,value=0,size_hint_y=None,height=dp(9))
        self.progress_box.add_widget(self.progress_label); self.progress_box.add_widget(self.progress_bar)
        self.root_box.add_widget(self.progress_box)
        self.content=ScrollView(do_scroll_x=False,bar_width=dp(3),scroll_type=['bars','content'])
        self.body=GridLayout(cols=1,spacing=dp(10),padding=[dp(12),dp(12)],size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter('height'))
        self.content.add_widget(self.body); self.root_box.add_widget(self.content)
        self.status=Label(text='Ready',size_hint_y=None,height=dp(25),font_size=sp(10),color=MUTED)
        self.root_box.add_widget(self.status)
        self.show_page('Home')
        return self.root_box
    def _header_paint(self,*_): self.header_bg.pos=self.header.pos; self.header_bg.size=self.header.size
    def open_menu(self,*_):
        names=['Home','Competition Day','Setup','Teams','Matches','My Team','Standings','Alliances','Charts','Win Rate','Analysis','Live Scout','Team Search','Scouts','Settings']
        menu=DropDown(auto_width=False,width=dp(250),max_height=Window.height-dp(90))
        for name in names:
            b=Button(text=name,size_hint_y=None,height=dp(44),background_normal='',background_color=MAROON if name==self.page else (0.93,0.94,0.96,1),color=WHITE if name==self.page else INK,font_size=sp(14))
            b.bind(on_release=lambda btn,n=name:(menu.select(n)))
            menu.add_widget(b)
        menu.bind(on_select=lambda instance,n:self.show_page(n))
        menu.open(self.menu_button)
    def set_progress(self,message,fraction):
        def update(_dt):
            self.progress_box.opacity=1; self.progress_box.disabled=False
            self.progress_label.text=str(message)
            self.progress_bar.value=max(0,min(100,float(fraction)*100))
        Clock.schedule_once(update,0)
    def hide_progress(self):
        self.progress_bar.value=0; self.progress_box.opacity=0; self.progress_box.disabled=True
    def _load_mobile_state(self):
        p=os.path.join(self.user_data_dir,'mobile_state.json')
        try:
            d=json.load(open(p,encoding='utf-8')); self.scouts=d.get('scouts',[]); self.watch_teams=d.get('watch_teams',[]); self.assignments=d.get('assignments',{})
            self.selected_team=int(d.get('selected_team',0) or 0)
            spath=d.get('session_path')
            if spath and os.path.exists(spath): self.session=core.Session.open(spath)
        except Exception: pass
    def save_state(self):
        p=os.path.join(self.user_data_dir,'mobile_state.json')
        try: json.dump({'scouts':self.scouts,'watch_teams':self.watch_teams,'assignments':self.assignments,'selected_team':self.selected_team,'session_path':self.session.path},open(p,'w',encoding='utf-8'),indent=2)
        except Exception as e: self.status.text=f'Save warning: {e}'
    def say(self,msg): self.status.text=str(msg)
    def add(self,w): self.body.add_widget(w)
    def label(self,text,size=14,color=INK,bold=False,height=None):
        l=Label(text=str(text),size_hint_y=None,height=dp(height or (30 if size<16 else 38)),font_size=sp(size),color=color,bold=bold,halign='left',valign='middle')
        l.bind(size=lambda o,v:setattr(o,'text_size',(v[0],None)))
        return l
    def button(self,text,fn,height=44):
        b=Button(text=text,size_hint_y=None,height=dp(height),background_normal='',background_color=MAROON,color=WHITE,font_size=sp(14))
        b.bind(on_release=lambda *_:fn()); return b
    def data_button(self,text,fn=None,bg=WHITE,fg=INK,height=44,bold=False):
        b=Button(text=str(text),size_hint_y=None,height=dp(height),background_normal='',background_down='',background_color=bg,color=fg,font_size=sp(13),bold=bold,halign='left',valign='middle',padding=[dp(12),dp(5)],shorten=False)
        b.bind(size=lambda obj,val:setattr(obj,'text_size',(max(dp(40),val[0]-dp(24)),None)))
        if fn: b.bind(on_release=lambda *_:fn())
        return b
    def team_color(self,number):
        return SELECTED if self.selected_team and int(number)==int(self.selected_team) else None
    def field(self,hint,value='',height=44,multiline=False):
        return TextInput(hint_text=hint,text=str(value),size_hint_y=None,height=dp(height),multiline=multiline,padding=[dp(10),dp(10)],font_size=sp(14),background_color=WHITE,foreground_color=INK,cursor_color=MAROON)
    def card(self,title=None):
        c=Card()
        if title: c.add_widget(self.label(title,16,MAROON,True,30))
        self.add(c); return c
    def show_page(self,name,*_):
        self.page=name; self.body.clear_widgets()
        fn=getattr(self,'page_'+name.lower().replace(' ','_'),None)
        if fn: fn()
        else: self.add(self.label(name+' is not available yet.',18))
    def page_home(self):
        self.add(self.label('Competition command center',21,MAROON,True,40))
        c=self.card('CURRENT EVENT')
        c.add_widget(self.label(self.session.event_name if self.session.loaded else 'No event loaded',18,INK,True))
        c.add_widget(self.label(f"Season {self.session.season}  •  {self.session.event_code or 'Choose an event in Setup'}",12,MUTED))
        c.add_widget(self.label(f"{len(self.session.teams)} teams  •  {len(self.session.matches)} matches  •  {len(self.session.predictions)} predictions",13))
        if self.session.loaded:
            a,b=self.session.accuracy(); c.add_widget(self.label(f'Prediction accuracy: {a}/{b} scored matches',13))
        quick=self.card('QUICK ACTIONS')
        for n in ['Setup','Matches','Teams','My Team','Live Scout','Team Search']:
            quick.add_widget(self.button(n,partial(self.show_page,n),40))
        c=self.card('MOBILE WORKSPACE')
        c.add_widget(self.label('The mobile edition carries the AutoScout 4.1.0 calculation engine, session format, FTCScout data client, CAP / OPR / EPA predictions, standings, alliance analysis, and export/report functions.',13))
    def page_competition_day(self):
        self.add(self.label('Competition day',21,MAROON,True,40))
        c=self.card('LIVE EVENT STATUS')
        c.add_widget(self.label(self.session.event_name if self.session.loaded else 'No event loaded',16,INK,True))
        c.add_widget(self.label(f'{sum(1 for m in self.session.matches if m.played)} of {len(self.session.matches)} matches completed',13,MUTED))
        c.add_widget(self.button('Refresh live match results',self.refresh_event))
        c.add_widget(self.button('Open full match schedule',lambda:self.show_page('Matches')))
        if self.session.matches:
            upcoming=next((p for p in self.session.predictions if not p.match.played),None)
            if upcoming:
                m=upcoming.match
                c.add_widget(self.label(f'Next unplayed: {m.label}  •  Red {m.red} vs Blue {m.blue}',14,MAROON,True))
                c.add_widget(self.button('Open next match',lambda:self.match_detail(upcoming)))
        w=self.card('WATCHLIST MATCHES')
        count=0
        for p in self.session.predictions:
            if any(n in self.watch_teams for n in p.match.teams):
                m=p.match; w.add_widget(self.label(f'{m.label}: Red {m.red} vs Blue {m.blue}',13)); count+=1
        if not count:w.add_widget(self.label('Add teams in Scouts to highlight their matches.',12,MUTED))
    def page_win_rate(self):
        self.add(self.label('Alliance win-rate model',21,MAROON,True,40))
        fit=self.session.strength_fit
        c=self.card('FITTED ALLIANCE STRENGTH CURVE')
        if fit:
            c.add_widget(self.label('Modeled chance of winning by combined alliance rating',12,MUTED,height=26))
            c.add_widget(self.label(fit.equation,12,MAROON,True,38))
            c.add_widget(self.label(f'Fit R²: {fit.r2:.3f}  •  {fit.n} alliance samples',12,MUTED))
            ratings=[float(t.strength) for t in self.session.teams.values()]
            if ratings:
                lo=max(0,min(ratings)); hi=max(ratings)
                if hi<=lo:hi=lo+1
                xs=[lo+(hi-lo)*i/30 for i in range(31)]
                c.add_widget(LineChart([(x,fit.predict(x)) for x in xs]))
                c.add_widget(self.label(f'Alliance rating: {lo:.1f} to {hi:.1f}     Win probability: 0–100%',10,MUTED,height=24))
                for x in [lo+(hi-lo)*i/5 for i in range(6)]:
                    c.add_widget(self.label(f'Total rating {x:.1f}  →  {fit.predict(x):.1f}% modeled win rate',11))
        else:c.add_widget(self.label('Not enough alliance data to fit the event-specific win-rate curve yet.',13,MUTED))
        c.add_widget(self.button('View alliance report',lambda:self.show_page('Alliances')))
    def page_setup(self):
        c=self.card('EVENT SETUP')
        c.add_widget(self.label('Load an FTC event from FTCScout. Event history is used to calculate CAP, OPR, and EPA.',12,MUTED))
        self.season_f=self.field('Season (e.g. 2026)',self.session.season); c.add_widget(self.season_f)
        self.event_f=self.field('FTCScout event code (exact event URL code)',self.session.event_code); c.add_widget(self.event_f)
        self.myteam_f=self.field('Your team number',self.session.my_team); c.add_widget(self.myteam_f)
        self.extra_f=self.field('Additional team numbers (comma separated)',','.join(map(str,self.session.extra_teams))); c.add_widget(self.extra_f)
        c.add_widget(self.button('Load event + history',self.load_event))
        c.add_widget(self.button('Refresh match results',self.refresh_event))
        s=self.card('SCHEDULE IMPORT / SESSION')
        self.schedule_f=self.field('Paste one match per line: Q1 12345 23456 vs 34567 45678',self.session.pasted_schedule,100,True); s.add_widget(self.schedule_f)
        s.add_widget(self.button('Use pasted schedule',self.apply_schedule))
        s.add_widget(self.button('Save session to app storage',self.save_session))
        s.add_widget(self.button('Export CSV report',self.export_csv))
        s.add_widget(self.button('Export HTML report',self.export_html))
    def load_event(self):
        try:
            season=int(self.season_f.text); code=self.event_f.text.strip().upper(); my=int(self.myteam_f.text or 0)
            extras=core.parse_team_list(self.extra_f.text)
            if not code: raise ValueError('Enter an FTCScout event code.')
            self.session.season=season; self.session.event_code=code; self.session.my_team=my; self.selected_team=my; self.session.extra_teams=extras
        except Exception as e: self.say(e); return
        self.set_progress('Connecting to FTCScout…',0.01)
        self.say('Loading event and team history…')
        def work():
            try:
                self.session.load(self.client,progress=self.set_progress,with_history=True)
                result=('ok','Loaded '+self.session.event_name)
            except Exception as e:
                result=('error',f'{type(e).__name__}: {e}')
            Clock.schedule_once(lambda dt:self._load_done(*result),0)
        threading.Thread(target=work,daemon=True).start()
    def _load_done(self,status,msg):
        self.hide_progress()
        if status=='ok':
            self.save_state(); self.say(msg + (f' — {len(self.session.team_numbers)} teams, {len(self.session.matches)} matches.' ))
            self.show_page('Home')
            if self.session.warnings:
                self.say(msg + ' Warning: ' + ' | '.join(self.session.warnings[:2]))
        else:
            self.say('Event load failed: '+msg)
            popup=Popup(title='Could not load event',content=Label(text=msg, color=INK),size_hint=(.9,.42))
            popup.open()
    def refresh_event(self):
        def work():
            try: n=self.session.refresh_results(self.client); msg=f'Refreshed results: {n} matches played.'
            except Exception as e: msg=f'Refresh failed: {e}'
            Clock.schedule_once(lambda dt:self._refresh_done(msg),0)
        threading.Thread(target=work,daemon=True).start(); self.set_progress('Refreshing match results…',0.1); self.say('Refreshing results…')
    def _refresh_done(self,msg):
        self.hide_progress(); self.save_state(); self.say(msg)
        if msg.startswith('Refresh failed:'):
            Popup(title='Refresh failed',content=Label(text=msg,color=INK),size_hint=(.9,.4)).open()
    def apply_schedule(self):
        self.session.pasted_schedule=self.schedule_f.text; self.session.api_matches=[]; self.session.compute(); self.save_state(); self.say(f'Imported {len(self.session.matches)} matches.'); self.show_page('Matches')
    def save_session(self):
        p=os.path.join(self.user_data_dir,f'autoscout_{self.session.season}_{self.session.event_code or "session"}.json')
        try: self.session.save(p); self.save_state(); self.say('Session saved: '+p)
        except Exception as e: self.say('Save failed: '+str(e))
    def export_csv(self):
        try:
            p=os.path.join(self.user_data_dir,'AutoScout_Report.csv'); core.export_csv(self.session,p); self.say('CSV exported: '+p)
        except Exception as e:self.say('CSV export failed: '+str(e))
    def export_html(self):
        try:
            p=os.path.join(self.user_data_dir,'AutoScout_Report.html'); core.export_html(self.session,p); self.say('HTML exported: '+p)
        except Exception as e:self.say('HTML export failed: '+str(e))
    def page_teams(self):
        self.add(self.label('Team performance',21,MAROON,True,40))
        if not self.session.teams: self.add(self.label('Load an event first.',14,MUTED)); return
        f=self.field('Search team number or name'); self.add(f)
        holder=Card(); self.add(holder)
        def render(*_):
            holder.clear_widgets(); rows=sorted(self.session.teams.values(),key=lambda t:t.cap,reverse=True)
            q=f.text.lower().strip()
            for t in rows:
                if q and q not in str(t.number) and q not in t.name.lower(): continue
                holder.add_widget(self.data_button(f'{"★  " if int(t.number)==int(self.selected_team or 0) else ""}{t.number}  {t.name or "Team"}   CAP {t.cap:.1f}  OPR {t.opr:.1f}  EPA {t.epa:.1f}',partial(self.team_detail,t.number),SELECTED_LIGHT if int(t.number)==int(self.selected_team or 0) else WHITE,INK,54,int(t.number)==int(self.selected_team or 0)))
        f.bind(text=render); render()
    def team_detail(self,n):
        self.selected_team=int(n)
        self.save_state()
        t=self.session.teams[n]; m=self.session.manual_for(n)
        c=Card(); self.add(c); c.add_widget(self.label(f'{n} — {t.name}',20,MAROON,True))
        for k in ['cap','opr','epa','proj_opr','auto','teleop','endgame','strength']:
            c.add_widget(self.label(f'{k.upper()}: {getattr(t,k,None)}',13))
        c.add_widget(self.label('Manual overrides (leave blank to use calculated value)',12,MUTED))
        fields={}
        for key in ['opr','auto','teleop','endgame','proj_opr','epa']:
            inp=self.field(key.upper()+' override',getattr(m,key) if getattr(m,key) is not None else '')
            c.add_widget(inp); fields[key]=inp
        def save():
            for key,inp in fields.items():
                try:setattr(m,key,float(inp.text) if inp.text.strip() else None)
                except ValueError: self.say('Invalid number for '+key); return
            self.session.compute(); self.save_state(); self.say('Team overrides saved.'); self.show_page('Teams')
        c.add_widget(self.button('Save team overrides',save))
        c.add_widget(self.button('Add to watchlist',lambda:self.add_watch(n)))
    def add_watch(self,n):
        if n not in self.watch_teams:self.watch_teams.append(n)
        self.save_state(); self.say(f'Team {n} added to watchlist.')
    def page_matches(self):
        self.add(self.label('Match predictions',21,MAROON,True,40))
        if not self.session.matches: self.add(self.label('Load an event or paste a schedule first.',14,MUTED)); return
        legend=self.card('ALLIANCE KEY')
        legend.add_widget(self.data_button('RED ALLIANCE  •  red = red win / red prediction',bg=RED_LIGHT,fg=RED,height=34,bold=True))
        legend.add_widget(self.data_button('BLUE ALLIANCE  •  blue = blue win / blue prediction',bg=BLUE_LIGHT,fg=BLUE,height=34,bold=True))
        f=self.field('Filter by match or team number'); self.add(f)
        holder=BoxLayout(orientation='vertical',spacing=dp(9),size_hint_y=None)
        holder.bind(minimum_height=holder.setter('height')); self.add(holder)
        def render(*_):
            holder.clear_widgets(); q=f.text.lower().strip()
            for p in self.session.predictions:
                mt=p.match; teams=mt.teams
                if q and q not in mt.label.lower() and not any(q in str(n) for n in teams): continue
                red='  /  '.join(map(str,mt.red)); blue='  /  '.join(map(str,mt.blue))
                watch='   ★ WATCHLIST' if any(n in self.watch_teams for n in teams) else ''
                winner=mt.winner or p.winner
                row=Card(padding=[dp(8),dp(8)],spacing=dp(4))
                heading=f'{mt.label}{watch}' + (f'    FINAL  {mt.red_score:g}–{mt.blue_score:g}' if mt.played else f'    PREDICTED WIN: {winner}')
                row.add_widget(self.data_button(heading,partial(self.match_detail,p),PAGE,INK,34,True))
                red_selected=bool(self.selected_team and any(int(n)==int(self.selected_team) for n in mt.red))
                blue_selected=bool(self.selected_team and any(int(n)==int(self.selected_team) for n in mt.blue))
                red_won=winner=='RED'; blue_won=winner=='BLUE'
                red_bg=SELECTED if red_selected else ((0.98,0.77,0.77,1) if red_won else RED_LIGHT)
                blue_bg=SELECTED if blue_selected else ((0.75,0.85,1,1) if blue_won else BLUE_LIGHT)
                red_prefix='🏆 ' if red_won else ''
                blue_prefix='🏆 ' if blue_won else ''
                row.add_widget(self.data_button(f'{red_prefix}RED   {red}     {p.red_pts:.1f} pts   •   {p.red_cow:.0%} win',partial(self.match_detail,p),red_bg,RED,40,red_selected or red_won))
                row.add_widget(self.data_button(f'{blue_prefix}BLUE  {blue}     {p.blue_pts:.1f} pts   •   {p.blue_cow:.0%} win',partial(self.match_detail,p),blue_bg,BLUE,40,blue_selected or blue_won))
                if red_selected or blue_selected:
                    selected_side='RED' if red_selected else 'BLUE'
                    row.add_widget(self.label(f'★ YOUR SELECTED TEAM IS ON THE {selected_side} ALLIANCE',10,MAROON,True,20))
                holder.add_widget(row)
        f.bind(text=render); render()
    def match_detail(self,p):
        mt=p.match; c=Card(); self.add(c); c.add_widget(self.label(f'{mt.label} prediction',20,MAROON,True))
        c.add_widget(self.data_button(f'RED ALLIANCE  {mt.red}   •   {p.red_pts:.1f} predicted points   •   {p.red_cow:.1%} win',bg=RED_LIGHT,fg=RED,height=48,bold=True))
        c.add_widget(self.data_button(f'BLUE ALLIANCE {mt.blue}   •   {p.blue_pts:.1f} predicted points   •   {p.blue_cow:.1%} win',bg=BLUE_LIGHT,fg=BLUE,height=48,bold=True))
        winner=mt.winner or p.winner
        win_bg=RED_LIGHT if winner=='RED' else BLUE_LIGHT if winner=='BLUE' else PAGE
        win_fg=RED if winner=='RED' else BLUE if winner=='BLUE' else INK
        c.add_widget(self.data_button(f'{"ACTUAL" if mt.played else "PREDICTED"} WINNER: {winner}',bg=win_bg,fg=win_fg,height=42,bold=True))
        if mt.played:c.add_widget(self.label(f'Actual score: {mt.red_score:g} - {mt.blue_score:g}',14))
        c.add_widget(self.button('Add scouting note for this match',lambda:self.note_for_match(mt.label)))
        c.add_widget(self.button('Back to matches',lambda:self.show_page('Matches')))
    def page_my_team(self):
        self.add(self.label('My team schedule',21,MAROON,True,40))
        self.add(self.label(f'Team {self.session.my_team}',14,MUTED))
        if not self.session.loaded:self.add(self.label('Load an event first.',14));return
        summary=self.session.my_summary(); t=summary['stats']
        if t:
            c=self.card('TEAM SNAPSHOT')
            for k in ['cap','opr','epa','rank','auto','teleop','endgame']:c.add_widget(self.label(f'{k.upper()}: {getattr(t,k,"n/a")}',13))
        c=self.card('MATCHES')
        for m in summary['matches']:
            c.add_widget(self.data_button(f'{m.prediction.match.label}  •  Opp {m.opponents}  •  {m.prediction.winner}  •  {m.cow:.0%}',partial(self.note_for_match,m.prediction.match.label),RED_LIGHT if m.prediction.winner=='RED' else BLUE_LIGHT if m.prediction.winner=='BLUE' else WHITE,RED if m.prediction.winner=='RED' else BLUE if m.prediction.winner=='BLUE' else INK,48,True))
    def page_standings(self):
        self.add(self.label('Predicted standings',21,MAROON,True,40))
        c=self.card('RANK • TEAM • W-L • RP • CAP')
        for r in self.session.table:
            selected=int(r.number)==int(self.selected_team or 0)
            team=self.session.teams.get(r.number)
            cap=getattr(team,'cap',0.0) if team else 0.0
            c.add_widget(self.data_button(f'{"★  " if selected else ""}{r.rank:>2}.  {r.number}  {r.wins}-{r.losses}  RP {r.rp:.1f}  CAP {cap:.1f}',partial(self.team_detail,r.number) if team else None,SELECTED_LIGHT if selected else WHITE,INK,42,selected))
    def page_alliances(self):
        self.add(self.label('Alliance selection',21,MAROON,True,40))
        if not self.session.loaded:self.add(self.label('Load an event first.'));return
        report=self.session.alliance_report(); c=self.card('ALLIANCE REPORT')
        for a in report.table[:40]:
            bg=SELECTED_LIGHT if self.selected_team and self.selected_team in a.teams else WHITE
            c.add_widget(self.data_button(f'{a.rank}. {a.teams}  CAP {a.cap_sum:.1f}  Win {a.win_rate:.1%}',bg=bg,fg=INK,height=40,bold=self.selected_team in a.teams if self.selected_team else False))
        c.add_widget(self.label('Partners for your team',15,MAROON,True))
        for a in report.partners:c.add_widget(self.label(f'{a.teams}  CAP {a.cap_sum:.1f}',13))
    def page_charts(self):
        self.add(self.label('Charts & trends',21,MAROON,True,40))
        if not self.session.teams:self.add(self.label('Load an event first.',14,MUTED));return
        teams=self.session.teams_by_cap()[:20]
        maximum=max([max(float(getattr(t,k,0) or 0) for k in ('cap','opr','epa')) for t in teams] or [1])
        c=self.card('TEAM PERFORMANCE  •  CAP / OPR / EPA')
        c.add_widget(self.label('Grouped horizontal bar chart. Bars are scaled to the highest displayed metric.',11,MUTED,height=28))
        legend=BoxLayout(size_hint_y=None,height=dp(24),spacing=dp(10))
        for name,col in [('CAP',MAROON),('OPR',BLUE),('EPA',(0.12,0.58,0.40,1))]:
            chip=BoxLayout(spacing=dp(4)); swatch=Widget(size_hint_x=None,width=dp(10))
            with swatch.canvas:
                Color(*col); rect=RoundedRectangle(radius=[dp(2)])
            swatch.bind(pos=lambda o,v,r=rect:setattr(r,'pos',o.pos),size=lambda o,v,r=rect:setattr(r,'size',o.size))
            chip.add_widget(swatch); chip.add_widget(Label(text=name,font_size=sp(10),color=INK)); legend.add_widget(chip)
        c.add_widget(legend)
        for t in teams:
            selected=bool(self.selected_team and int(t.number)==int(self.selected_team))
            block=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(78),padding=[dp(5),dp(3)],spacing=dp(1))
            with block.canvas.before:
                Color(*(SELECTED_LIGHT if selected else (1,1,1,1))); bg=RoundedRectangle(radius=[dp(5)])
            block.bind(pos=lambda o,v,r=bg:setattr(r,'pos',o.pos),size=lambda o,v,r=bg:setattr(r,'size',o.size))
            block.add_widget(self.data_button(f'{"★ " if selected else ""}{t.number}  {t.name or ""}',partial(self.team_detail,t.number),SELECTED_LIGHT if selected else WHITE,INK,23,selected))
            for name,key,col in [('CAP','cap',MAROON),('OPR','opr',BLUE),('EPA','epa',(0.12,0.58,0.40,1))]:
                block.add_widget(BarTrack(name,float(getattr(t,key,0) or 0),maximum,col))
            c.add_widget(block)
        c.add_widget(self.label(f'Showing the top {len(teams)} teams by CAP. Select a team row to open its metrics and overrides.',11,MUTED, height=34))
        if self.session.matches:
            trend=self.card('MATCH WIN PROBABILITY')
            for p in self.session.predictions[:12]:
                winner=p.match.winner or p.winner
                redcol=RED if winner=='RED' else MUTED
                bluecol=BLUE if winner=='BLUE' else MUTED
                trend.add_widget(self.data_button(f'{p.match.label}   RED {p.red_cow:.0%}  |  BLUE {p.blue_cow:.0%}   •   {winner or "NO CLEAR WINNER"}',partial(self.match_detail,p),RED_LIGHT if winner=='RED' else BLUE_LIGHT if winner=='BLUE' else PAGE,redcol if winner=='RED' else bluecol,34,winner in ('RED','BLUE')))
    def page_analysis(self):
        self.add(self.label('Prediction analysis',21,MAROON,True,40))
        if not self.session.loaded:self.add(self.label('Load an event first.'));return
        try:
            rep=core.analyze(self.session); c=self.card('ANALYSIS REPORT')
            for line in core._summary(self.session,rep):c.add_widget(self.label(line,12))
        except Exception as e:self.add(self.label('Analysis unavailable: '+str(e),12))
    def page_live_scout(self):
        self.add(self.label('Live scouting & notes',21,MAROON,True,40))
        c=self.card('STREAM')
        url=self.field('YouTube stream URL',self.session.live_stream_url); c.add_widget(url)
        def open_stream():
            self.session.live_stream_url=url.text.strip(); self.save_state();
            if self.session.live_stream_url:webbrowser.open(self.session.live_stream_url)
        c.add_widget(self.button('Save & open stream',open_stream))
        n=self.card('MATCH NOTE')
        match=self.field('Match label (e.g. Q-1)',getattr(self,'_pending_match','')); self._pending_match=''; n.add_widget(match)
        team=self.field('Team number'); n.add_widget(team)
        category=Spinner(text='General',values=['General','Autonomous','TeleOp','Endgame','Driver','Reliability','Strategy'],size_hint_y=None,height=dp(44)); n.add_widget(category)
        note=self.field('Observation / scouting note',height=100,multiline=True); n.add_widget(note)
        def save_note():
            key=match.text.strip() or 'General'; self.session.live_notes.setdefault(key,[]).append({'team':team.text.strip(),'category':category.text,'text':note.text.strip(),'pinned':False})
            self.save_session(); self.say('Note saved.'); self.show_page('Live Scout')
        n.add_widget(self.button('Save note',save_note))
        notes=self.card('SAVED NOTES')
        for key,items in self.session.live_notes.items():
            for item in items:notes.add_widget(self.label(f'{key} • Team {item.get("team")} • {item.get("category")}: {item.get("text")}',12))
    def note_for_match(self,label):
        self._pending_match=label
        self.show_page('Live Scout')
    def page_team_search(self):
        self.add(self.label('FTC team research',21,MAROON,True,40))
        c=self.card('SEARCH ANY TEAM')
        f=self.field('Team number or search phrase'); c.add_widget(f)
        result=Card(); c.add_widget(result)
        def search():
            result.clear_widgets(); result.add_widget(self.label('Searching FTCScout…',12))
            def work():
                try:
                    q=f.text.strip(); data=self.client.team(int(q)) if q.isdigit() else self.client.search_teams(q)
                    msg=json.dumps(data,indent=2)[:5000]
                except Exception as e:msg='Search failed: '+str(e)
                Clock.schedule_once(lambda dt:(result.clear_widgets(),result.add_widget(self.label(msg,11))),0)
            threading.Thread(target=work,daemon=True).start()
        c.add_widget(self.button('Search FTCScout',search))
    def page_scouts(self):
        self.add(self.label('Scout assignments & watchlist',21,MAROON,True,40))
        c=self.card('TRACKED TEAMS')
        tf=self.field('Team numbers separated by commas'); c.add_widget(tf)
        c.add_widget(self.button('Add teams',lambda:self._add_watch_text(tf.text)))
        for n in self.watch_teams:c.add_widget(self.label(f'★ Team {n}',13))
        s=self.card('SCOUT ROSTER')
        sf=self.field('Scout / team member name'); s.add_widget(sf)
        s.add_widget(self.button('Add scout',lambda:self._add_scout(sf.text)))
        for name in self.scouts:
            row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6))
            row.add_widget(self.label(name,13))
            spn=Spinner(text=str(self.assignments.get(name,'Unassigned')),values=['Unassigned']+[str(x) for x in self.watch_teams],size_hint_x=.5)
            spn.bind(text=lambda obj,val,nm=name:self._assign(nm,val)); row.add_widget(spn); s.add_widget(row)
            assigned=self.assignments.get(name)
            if assigned:
                labels=[m.label for m in self.session.matches if assigned in m.teams]
                s.add_widget(self.label(f'{name} watches team {assigned}: '+(', '.join(labels) or 'No matches loaded'),11,MUTED))
    def _add_watch_text(self,text):
        for n in core.parse_team_list(text):
            if n not in self.watch_teams:self.watch_teams.append(n)
        self.save_state(); self.show_page('Scouts')
    def _add_scout(self,name):
        name=name.strip()
        if name and name not in self.scouts:self.scouts.append(name)
        self.save_state(); self.show_page('Scouts')
    def _assign(self,name,value):
        self.assignments[name]=int(value) if value.isdigit() else 0; self.save_state()
    def page_settings(self):
        self.add(self.label('Settings & model controls',21,MAROON,True,40))
        c=self.card('PREDICTION BASIS')
        spin=Spinner(text=self.session.settings.basis,values=['CAP','OPR','EPA'],size_hint_y=None,height=dp(44));c.add_widget(spin)
        def setbasis():self.session.settings.basis=spin.text;self.session.compute();self.save_state();self.say('Prediction basis updated.');self.show_page('Settings')
        c.add_widget(self.button('Apply rating basis',setbasis))
        c.add_widget(self.label(self.session.epa_summary(),12,MUTED))
        c.add_widget(self.label('Session data is saved locally on this device. FTCScout requests are cached for offline/reduced-connectivity use.',12))
        c.add_widget(self.button('Save session',self.save_session))
        c.add_widget(self.button('Export CSV',self.export_csv));c.add_widget(self.button('Export HTML',self.export_html))

if __name__ == '__main__': AutoScoutMobile().run()
