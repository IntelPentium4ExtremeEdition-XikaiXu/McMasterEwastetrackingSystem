#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McMaster e-waste tracker v3: interactive map checkboxes and route order."""
import csv, json, math, os, tempfile, tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
try:
    from PIL import Image, ImageTk
except ImportError:
    raise SystemExit("缺少 Pillow。请运行: python3 -m pip install pillow")

APP_TITLE="McMaster E-Waste Map Tracker v4"
LANG = {
 "en": {
  "title":"McMaster E-Waste Map Tracker v4", "date":"Date", "load":"Load",
  "all":"Select All", "medical_only":"Medical Only", "route":"Calculate and Show Route",
  "save_plan":"Save Daily Selection", "hint":"Select bins directly on the map. Medical is always selected.",
  "record":"Selected Location Record", "click":"Click a location button on the map",
  "status":"Status", "items":"Visible Items", "notes":"Notes", "save_record":"Save Location Record",
  "export":"Export CSV", "language":"Language", "missing_map":"Map Missing",
  "missing_map_msg":"Place {name} beside this program.", "json_error":"JSON Error",
  "date_error":"Date Error", "date_error_msg":"Enter a date in YYYY-MM-DD format.",
  "loaded":"Loaded {day}. Select locations visually on the map; building abbreviations are optional.",
  "selected":"{count} locations selected. Click Calculate and Show Route.",
  "plan_saved":"Daily selection saved to JSON.", "route_prefix":"Suggested order: ",
  "choose":"Please Select", "choose_msg":"Click a location name on the map first.",
  "record_saved":"Record saved for {name}.", "done":"Done", "exported":"Exported: {path}",
  "location":"Map location: {name} [{kind}]", "home":"Dalewood Start", "fixed":"Required",
  "indoor":"Indoor", "small_indoor":"Small Indoor", "outdoor":"Outdoor",
  "unchecked":"Not Checked", "empty":"Empty", "low":"Low", "medium":"Medium", "high":"High",
  "full":"Full", "no_access":"Cannot Access", "missing":"Bin Missing"
 },
 "zh": {
  "title":"McMaster 电子废物箱地图追踪器 v4", "date":"日期", "load":"载入",
  "all":"全部选择", "medical_only":"只保留 Medical", "route":"计算并显示路线",
  "save_plan":"保存当天选择", "hint":"直接在地图上勾选回收箱。Medical 固定勾选。",
  "record":"当前地点记录", "click":"点击地图上的地点按钮", "status":"状态",
  "items":"可见物品", "notes":"备注", "save_record":"保存地点记录", "export":"导出 CSV",
  "language":"语言", "missing_map":"缺少地图", "missing_map_msg":"请把 {name} 放在程序旁边。",
  "json_error":"JSON 错误", "date_error":"日期错误", "date_error_msg":"请输入 YYYY-MM-DD 格式日期。",
  "loaded":"已载入 {day}。直接按地图位置勾选，不必记建筑缩写。",
  "selected":"当前选择 {count} 个地点。点击“计算并显示路线”。",
  "plan_saved":"当天勾选已保存到 JSON。", "route_prefix":"建议顺序：",
  "choose":"请选择", "choose_msg":"请先点击地图上的地点名称。",
  "record_saved":"已保存 {name} 的记录。", "done":"完成", "exported":"已导出：{path}",
  "location":"地图位置：{name} [{kind}]", "home":"Dalewood 出发点", "fixed":"固定检查",
  "indoor":"室内", "small_indoor":"小型室内", "outdoor":"室外",
  "unchecked":"未检查", "empty":"空", "low":"少量", "medium":"中等", "high":"较多",
  "full":"已满", "no_access":"无法进入", "missing":"箱体不存在"
 }
}
BASE=Path(__file__).resolve().parent
MAP_FILE=BASE/"mcmaster_ewaste_map.png"
DATA_FILE=BASE/"ewaste_bin_data.json"
# x/y are positions on the supplied 2000 x 1109 campus-map screenshot.
# Short location-oriented labels are used because the map position is the main identifier.
BINS=[
 {"id":"ABB","name":"ABB","kind":"室内","x":1280,"y":650},
 {"id":"CNH","name":"CNH","kind":"室内","x":1565,"y":250},
 {"id":"HSC","name":"HSC","kind":"室内","x":1705,"y":525},
 {"id":"ITB","name":"ITB","kind":"室内","x":1345,"y":840},
 {"id":"LSB","name":"LSB","kind":"室内","x":1640,"y":590},
 {"id":"MDCL","name":"MDCL","kind":"室内","x":1675,"y":640},
 {"id":"MIP_ATRIUM","name":"MIP","kind":"室内","x":1608,"y":390},
 {"id":"RECYCLING_ROOM","name":"Recycle","kind":"室内","x":1608,"y":340},
 {"id":"MILLS_SECURE","name":"Mills","kind":"小型室内","x":1618,"y":430},
 {"id":"MUSC_SMALL","name":"MUSC","kind":"小型室内","x":1415,"y":510},
 {"id":"BSB","name":"BSB","kind":"室外","x":1410,"y":485},
 {"id":"CSB","name":"CSB","kind":"室外","x":785,"y":520},
 {"id":"ETB","name":"ETB","kind":"室外","x":1405,"y":875},
 {"id":"GSB","name":"GSB","kind":"室外","x":1300,"y":455},
 {"id":"JHE","name":"JHE","kind":"室外","x":1395,"y":600},
 {"id":"MEDICAL","name":"Medical","kind":"固定检查","x":1655,"y":830,"required":True},
]
HOME={"id":"HOME","name":"Dalewood 出发点","x":1940,"y":1060}
STATUS_KEYS=["unchecked","empty","low","medium","high","full","no_access","missing"]

def new_data(): return {"schema_version":3,"bins":BINS,"observations":{},"daily_plans":{},"created_at":datetime.now().isoformat(timespec="seconds")}
def save(d):
 d["updated_at"]=datetime.now().isoformat(timespec="seconds")
 fd,tmp=tempfile.mkstemp(prefix="ewaste_",suffix=".json",dir=BASE)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,DATA_FILE)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
def load():
 if not DATA_FILE.exists(): d=new_data(); save(d); return d
 try:
  d=json.loads(DATA_FILE.read_text(encoding="utf-8")); d.setdefault("observations",{}); d.setdefault("daily_plans",{}); d["bins"]=BINS; return d
 except Exception as e:
  messagebox.showerror("JSON Error / JSON 错误",str(e)); return new_data()
def dist(a,b): return math.hypot(a["x"]-b["x"],a["y"]-b["y"])
def length(r): return sum(dist(r[i],r[i+1]) for i in range(len(r)-1))
def optimize(stops):
 rem=stops[:]; r=[HOME]; cur=HOME
 while rem:
  q=min(rem,key=lambda z:dist(cur,z)); r.append(q); rem.remove(q); cur=q
 r.append(HOME)
 changed=True
 while changed:
  changed=False
  for i in range(1,len(r)-2):
   for j in range(i+2,len(r)-1):
    n=r[:i]+r[i:j][::-1]+r[j:]
    if length(n)<length(r)-0.01: r=n; changed=True
 return r

class App(tk.Tk):
 def __init__(self):
  super().__init__(); self.title(APP_TITLE); self.geometry("1280x820"); self.minsize(980,650)
  if not MAP_FILE.exists(): messagebox.showerror(self.t("missing_map"),self.t("missing_map_msg",name=MAP_FILE.name)); self.destroy(); return
  self.lang="en"; self.data=load(); self.vars={}; self.windows=[]; self.route_ids=[]; self.selected=None; self.ui={}
  self.build(); self.after(100,self.redraw); self.protocol("WM_DELETE_WINDOW",self.close)
 def t(self,key,**kw): return LANG[self.lang][key].format(**kw)
 def status_values(self): return [self.t(k) for k in STATUS_KEYS]
 def build(self):
  top=ttk.Frame(self,padding=8); top.pack(fill="x"); self.ui["top"]=top
  self.ui["title"]=ttk.Label(top,text=self.t("title"),font=("TkDefaultFont",17,"bold")); self.ui["title"].pack(side="left")
  self.ui["date_label"]=ttk.Label(top,text=self.t("date")); self.ui["date_label"].pack(side="left",padx=(20,3)); self.day=tk.StringVar(value=date.today().isoformat()); ttk.Entry(top,textvariable=self.day,width=12).pack(side="left")
  self.ui["load"]=ttk.Button(top,text=self.t("load"),command=self.load_day); self.ui["load"].pack(side="left",padx=4)
  self.ui["all"]=ttk.Button(top,text=self.t("all"),command=self.all_on); self.ui["all"].pack(side="left",padx=4)
  self.ui["medical_only"]=ttk.Button(top,text=self.t("medical_only"),command=self.only_required); self.ui["medical_only"].pack(side="left")
  self.ui["route"]=ttk.Button(top,text=self.t("route"),command=self.make_route); self.ui["route"].pack(side="left",padx=8)
  self.ui["save_plan"]=ttk.Button(top,text=self.t("save_plan"),command=self.save_plan); self.ui["save_plan"].pack(side="left")
  self.ui["language_label"]=ttk.Label(top,text=self.t("language")); self.ui["language_label"].pack(side="left",padx=(12,3))
  self.language_var=tk.StringVar(value="English"); langbox=ttk.Combobox(top,textvariable=self.language_var,values=["English","中文"],state="readonly",width=8); langbox.pack(side="left"); langbox.bind("<<ComboboxSelected>>",self.change_language)
  self.info=tk.StringVar(value=self.t("hint")); tk.Label(self,textvariable=self.info,bg="#fff3cd",anchor="w",padx=8,pady=5).pack(fill="x",padx=8)
  body=ttk.Panedwindow(self,orient="horizontal"); body.pack(fill="both",expand=True,padx=8,pady=8)
  mapframe=ttk.Frame(body); self.side=ttk.LabelFrame(body,text=self.t("record"),padding=10); body.add(mapframe,weight=5); body.add(self.side,weight=1)
  self.canvas=tk.Canvas(mapframe,bg="#ddd",highlightthickness=0); xs=ttk.Scrollbar(mapframe,orient="horizontal",command=self.canvas.xview); ys=ttk.Scrollbar(mapframe,orient="vertical",command=self.canvas.yview)
  self.canvas.configure(xscrollcommand=xs.set,yscrollcommand=ys.set); self.canvas.grid(row=0,column=0,sticky="nsew"); ys.grid(row=0,column=1,sticky="ns"); xs.grid(row=1,column=0,sticky="ew"); mapframe.rowconfigure(0,weight=1); mapframe.columnconfigure(0,weight=1); self.canvas.bind("<Configure>",lambda e:self.redraw())
  self.place_name=tk.StringVar(value=self.t("click")); ttk.Label(self.side,textvariable=self.place_name,font=("TkDefaultFont",11,"bold"),wraplength=220).pack(anchor="w")
  self.ui["status_label"]=ttk.Label(self.side,text=self.t("status")); self.ui["status_label"].pack(anchor="w",pady=(12,2)); self.status=tk.StringVar(value=self.t("unchecked")); self.status_box=ttk.Combobox(self.side,textvariable=self.status,values=self.status_values(),state="readonly"); self.status_box.pack(fill="x")
  self.ui["items_label"]=ttk.Label(self.side,text=self.t("items")); self.ui["items_label"].pack(anchor="w",pady=(10,2)); self.items=tk.Text(self.side,width=26,height=7,wrap="word"); self.items.pack(fill="x")
  self.ui["notes_label"]=ttk.Label(self.side,text=self.t("notes")); self.ui["notes_label"].pack(anchor="w",pady=(10,2)); self.notes=tk.Text(self.side,width=26,height=7,wrap="word"); self.notes.pack(fill="x")
  self.ui["save_record"]=ttk.Button(self.side,text=self.t("save_record"),command=self.save_record); self.ui["save_record"].pack(fill="x",pady=(10,4)); self.ui["export"]=ttk.Button(self.side,text=self.t("export"),command=self.export); self.ui["export"].pack(fill="x"); self.load_day()
 def change_language(self,_=None):
  old_status=self.status.get(); old_values=self.status_values(); old_key=STATUS_KEYS[old_values.index(old_status)] if old_status in old_values else "unchecked"
  self.lang="zh" if self.language_var.get()=="中文" else "en"; self.title(self.t("title")); self.ui["title"].config(text=self.t("title")); self.ui["date_label"].config(text=self.t("date")); self.ui["load"].config(text=self.t("load")); self.ui["all"].config(text=self.t("all")); self.ui["medical_only"].config(text=self.t("medical_only")); self.ui["route"].config(text=self.t("route")); self.ui["save_plan"].config(text=self.t("save_plan")); self.ui["language_label"].config(text=self.t("language")); self.side.config(text=self.t("record")); self.ui["status_label"].config(text=self.t("status")); self.ui["items_label"].config(text=self.t("items")); self.ui["notes_label"].config(text=self.t("notes")); self.ui["save_record"].config(text=self.t("save_record")); self.ui["export"].config(text=self.t("export")); self.status_box.config(values=self.status_values()); self.status.set(self.t(old_key)); self.info.set(self.t("hint")); self.redraw()
 def redraw(self):
  if not self.winfo_exists(): return
  self.canvas.delete("all"); self.windows=[]
  raw=Image.open(MAP_FILE); cw=max(self.canvas.winfo_width(),700); ch=max(self.canvas.winfo_height(),500)
  scale=min(cw/raw.width,ch/raw.height); self.scale=scale
  im=raw.resize((int(raw.width*scale),int(raw.height*scale)),Image.Resampling.LANCZOS); self.photo=ImageTk.PhotoImage(im)
  self.canvas.create_image(0,0,image=self.photo,anchor="nw",tags="map"); self.canvas.config(scrollregion=(0,0,im.width,im.height))
  # route underneath widgets
  if hasattr(self,"current_route") and self.current_route:
   pts=[]
   for p in self.current_route: pts += [p["x"]*scale,p["y"]*scale]
   self.canvas.create_line(*pts,fill="#0057d9",width=4,arrow=tk.LAST,smooth=False)
  for b in BINS:
   v=self.vars.setdefault(b["id"],tk.BooleanVar(value=bool(b.get("required"))))
   frame=tk.Frame(self.canvas,bg="#ffffff",bd=1,relief="solid")
   cb=tk.Checkbutton(frame,variable=v,bg="#ffffff",activebackground="#dcecff",command=self.plan_changed)
   cb.pack(side="left"); btn=tk.Button(frame,text=b["name"],font=("TkDefaultFont",8,"bold"),bg="#d7f5d7" if b.get("required") else "white",command=lambda q=b:self.open_record(q),padx=2,pady=0); btn.pack(side="left")
   if b.get("required"): cb.select(); cb.configure(state="disabled")
   self.windows.append(self.canvas.create_window(b["x"]*scale,b["y"]*scale,window=frame,anchor="center"))
  # Home marker
  self.canvas.create_oval((HOME["x"]*scale-7,HOME["y"]*scale-7,HOME["x"]*scale+7,HOME["y"]*scale+7),fill="#0057d9",outline="white",width=2)
 def plan_changed(self): self.info.set(self.t("selected",count=sum(v.get() for v in self.vars.values())))
 def valid_day(self):
  try:return date.fromisoformat(self.day.get().strip()).isoformat()
  except ValueError:messagebox.showerror(self.t("date_error"),self.t("date_error_msg"));return None
 def load_day(self):
  d=self.valid_day()
  if not d:return
  plan=set(self.data["daily_plans"].get(d,[]))
  for b in BINS:self.vars.setdefault(b["id"],tk.BooleanVar()).set(b["id"] in plan or bool(b.get("required")))
  self.current_route=[]; self.redraw(); self.info.set(self.t("loaded",day=d))
 def all_on(self):
  for v in self.vars.values():v.set(True)
  self.redraw(); self.plan_changed()
 def only_required(self):
  for b in BINS:self.vars[b["id"]].set(bool(b.get("required")))
  self.redraw(); self.plan_changed()
 def save_plan(self):
  d=self.valid_day()
  if not d:return
  self.data["daily_plans"][d]=[b["id"] for b in BINS if self.vars[b["id"]].get()];save(self.data);self.info.set(self.t("plan_saved"))
 def make_route(self):
  chosen=[b for b in BINS if self.vars[b["id"]].get()]; self.current_route=optimize(chosen); self.save_plan(); self.redraw()
  names=" → ".join(p["name"] for p in self.current_route); self.info.set(self.t("route_prefix")+names)
 def kind_text(self,kind):
  return self.t({"室内":"indoor","小型室内":"small_indoor","室外":"outdoor","固定检查":"fixed"}.get(kind,"indoor"))
 def localize_status(self,key): return self.t(key if key in STATUS_KEYS else "unchecked")
 def current_status_key(self):
  vals=self.status_values(); return STATUS_KEYS[vals.index(self.status.get())] if self.status.get() in vals else "unchecked"
 def open_record(self,b):
  self.selected=b; self.place_name.set(self.t("location",name=b["name"],kind=self.kind_text(b["kind"]))); d=self.valid_day(); rec=self.data["observations"].get(d,{}).get(b["id"],{})
  self.status.set(self.localize_status(rec.get("status_key","unchecked"))); self.items.delete("1.0","end");self.items.insert("1.0",rec.get("visible_items",""));self.notes.delete("1.0","end");self.notes.insert("1.0",rec.get("notes",""))
 def save_record(self):
  d=self.valid_day()
  if not d or not self.selected:messagebox.showinfo(self.t("choose"),self.t("choose_msg"));return
  self.data["observations"].setdefault(d,{})[self.selected["id"]]={"status_key":self.current_status_key(),"status":self.status.get(),"visible_items":self.items.get("1.0","end").strip(),"notes":self.notes.get("1.0","end").strip(),"recorded_at":datetime.now().isoformat(timespec="seconds")};save(self.data);self.info.set(self.t("record_saved",name=self.selected["name"]))
 def export(self):
  p=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
  if not p:return
  names={b["id"]:b["name"] for b in BINS}
  with open(p,"w",newline="",encoding="utf-8-sig") as f:
   w=csv.writer(f);w.writerow(["日期","地点","状态","可见物品","备注","记录时间"])
   for d in sorted(self.data["observations"]):
    for bid,r in self.data["observations"][d].items():w.writerow([d,names.get(bid,bid),r.get("status",""),r.get("visible_items",""),r.get("notes",""),r.get("recorded_at","")])
  messagebox.showinfo(self.t("done"),self.t("exported",path=p))
 def close(self):save(self.data);self.destroy()
if __name__=="__main__":App().mainloop()
