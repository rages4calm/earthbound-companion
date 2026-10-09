// SPDX-License-Identifier: GPL-3.0-or-later
package org.earthbound.companion;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.widget.*;
import java.io.*;
import java.security.MessageDigest;
import java.util.*;

public final class LauncherActivity extends Activity {
 private static final int IMPORT=1,IMPORT_PHONE=2,EXPORT_PHONE=3;
 private final Set<String> originalHashes=new HashSet<>(Arrays.asList("4e01c943711d32c41e85cb858d9058169e7c8b1739fc7dc0a211e441f9631b9b","01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549","792370574832629c0dc436bbc5b3a3993a8670e7e5fc3e3a5b467791ce514462"));
 private final Set<String> reduxHashes=new HashSet<>(Arrays.asList("4b5f1c5ac76e4bdcce2dc66a2e8ef95b659e561d3cadebefa66efb85c0be5236","d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb"));
 private TextView status;private LinearLayout page;private SharedPreferences preferences;
 private File pack,session;private boolean importing;
 private final Map<String,CheckBox> checks=new LinkedHashMap<>();private final Map<String,EditText> numbers=new LinkedHashMap<>();
 @Override public void onCreate(Bundle state){super.onCreate(state);preferences=getSharedPreferences("companion",MODE_PRIVATE);
  ScrollView scroll=new ScrollView(this);page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);page.setPadding(24,24,24,24);scroll.addView(page);setContentView(scroll);
  text("EarthBound Companion · Android Preview",24);
  text("Device gameplay testing is pending. Import an Original or Redux assets.pak generated privately by Companion on a computer. ROM conversion and new Story Shuffle generation are not available on Android yet.",16);
  button("Import game data",()->pick(IMPORT,"*/*"));
  Spinner edition=new Spinner(this);edition.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Original","Redux"}));edition.setSelection(preferences.getInt("edition",0));page.addView(edition);edition.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onNothingSelected(android.widget.AdapterView<?> v){}public void onItemSelected(android.widget.AdapterView<?> v,android.view.View view,int position,long id){preferences.edit().putInt("edition",position).apply();select();}});
  button("Play",()->play(false));button("Resume quick save",()->play(true));
  text("Display and gameplay",20);
  check("integer_scale","Integer scaling",false);number("filter","Filter: 0 nearest, 1 Scale2x, 2 linear",1,0,2);number("aspect","Aspect: 0 widescreen, 1 classic, 2 ultrawide",0,0,2);
  check("wide_fov","Wide field of view",true);check("tilt_shift","Depth effect",true);check("color_grading","Color grading",true);check("scanlines","Scanlines",false);
  check("original_title","Original title presentation in Redux",false);check("hq_audio","HQ audio",true);check("nintendo_labels","Nintendo button labels",false);
  number("volume","Sound volume",80,0,100);number("music_volume","Music volume",75,0,100);number("sprint","Hold Y sprint: 0 off, 1 ×1.5, 2 ×2",1,0,2);
  check("instant_text","Instant text",true);check("no_homesickness","Disable homesickness",true);check("no_dad_calls","Disable Dad calls",false);
  number("exp_multiplier","Experience multiplier",1,1,16);number("money_multiplier","Money multiplier",1,1,16);number("fast_forward_multiplier","Fast-forward multiplier",3,2,16);number("quick_slot","Quick-save slot (0–4)",0,0,4);number("deadzone","Controller deadzone",8000,2000,30000);
  text("Save transfer",20);text("Normal phone saves can move between platforms. Quick saves stay on the engine that created them. App removal deletes this app's private data: export your phone save first.",16);
  button("Export phone save",()->{select();if(session==null)return;Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.setType("application/octet-stream");intent.putExtra(Intent.EXTRA_TITLE,"earthbound.srm");startActivityForResult(intent,EXPORT_PHONE);});
  button("Import phone save",()->pick(IMPORT_PHONE,"*/*"));
  status=text("",16);select();
 }
 private TextView text(String value,int size){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setPadding(0,8,0,8);page.addView(t);return t;}
 private void button(String title,Runnable task){Button b=new Button(this);b.setText(title);b.setOnClickListener(v->{if(importing){message("Please wait for the import to finish.");return;}try{task.run();}catch(Exception e){message(e.getMessage());}});page.addView(b);}
 private void check(String key,String title,boolean initial){CheckBox c=new CheckBox(this);c.setText(title);c.setChecked(preferences.getBoolean(key,initial));checks.put(key,c);page.addView(c);}
 private void number(String key,String title,int initial,int min,int max){text(title,16);EditText e=new EditText(this);e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);e.setText(Integer.toString(preferences.getInt(key,initial)));e.setTag(new int[]{min,max});numbers.put(key,e);page.addView(e);}
 private void message(String value){if(status!=null)status.setText(value==null?"Operation failed.":value);}
 private void select(){boolean redux=preferences.getInt("edition",0)==1;String hash=preferences.getString(redux?"redux_hash":"original_hash","");if(hash.isEmpty()){pack=null;session=null;message("Import "+(redux?"Redux":"Original")+" data to play.");return;}File root=new File(getFilesDir(),"ContentProfiles/"+hash);pack=new File(root,"assets.pak");session=new File(root,"Game");session.mkdirs();message((redux?"Redux":"Original")+" selected. Saves are separate for each data pack.");}
 private void pick(int request,String type){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(type);startActivityForResult(i,request);}
 private static String hash(byte[] bytes)throws Exception{StringBuilder s=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))s.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return s.toString();}
 private byte[] read(Uri uri,int limit)throws Exception{try(InputStream in=getContentResolver().openInputStream(uri);ByteArrayOutputStream out=new ByteArrayOutputStream()){if(in==null)throw new IOException("Cannot read selected file.");byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1){if(out.size()+n>limit)throw new IOException("Selected file exceeds the import size limit.");out.write(b,0,n);}return out.toByteArray();}}
 private static void atomic(File path,byte[] bytes)throws Exception{File parent=path.getParentFile();if(!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Cannot create data folder.");File temp=new File(parent,path.getName()+".import");try(FileOutputStream out=new FileOutputStream(temp)){out.write(bytes);out.getFD().sync();}java.nio.file.Files.move(temp.toPath(),path.toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING,java.nio.file.StandardCopyOption.ATOMIC_MOVE);}
 @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null||data.getData()==null)return;Uri uri=data.getData();importing=true;message("Working…");File chosenSession=session;new Thread(()->{try{
  if(request==IMPORT){byte[] bytes=read(uri,128*1024*1024);String sha=hash(bytes);boolean redux=reduxHashes.contains(sha);if(!redux&&!originalHashes.contains(sha))throw new IOException("This is not a supported Original / Redux data pack. Generate it using Companion; ROMs and arbitrary patched packs cannot be imported.");File root=new File(getFilesDir(),"ContentProfiles/"+sha);atomic(new File(root,"assets.pak"),bytes);preferences.edit().putString(redux?"redux_hash":"original_hash",sha).putInt("edition",redux?1:0).apply();}
  else if(request==IMPORT_PHONE){if(chosenSession==null)throw new IOException("Select game data first.");byte[] bytes=read(uri,8192);if(bytes.length!=8192)throw new IOException("A phone save must be exactly 8192 bytes.");File save=new File(chosenSession,"saves/earthbound.srm");if(save.exists())atomic(new File(chosenSession,"Backups/earthbound-"+System.currentTimeMillis()+".srm"),java.nio.file.Files.readAllBytes(save.toPath()));atomic(save,bytes);}
  else if(request==EXPORT_PHONE){if(chosenSession==null)throw new IOException("Select game data first.");File save=new File(chosenSession,"saves/earthbound.srm");try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){if(out==null)throw new IOException("Cannot write export.");out.write(java.nio.file.Files.readAllBytes(save.toPath()));}}
  runOnUiThread(()->{importing=false;select();message("Operation complete. "+preferences.getString(preferences.getInt("edition",0)==1?"redux_hash":"original_hash","").substring(0,8));});
 }catch(Exception e){runOnUiThread(()->{importing=false;message(e.getMessage());});}},"companion-import").start();}
 private void play(boolean resume)throws Exception{select();if(pack==null||!pack.isFile())throw new IOException("Import the selected edition's game data first.");boolean redux=preferences.getInt("edition",0)==1;File original=new File(getFilesDir(),"ContentProfiles/"+preferences.getString("original_hash","")+"/assets.pak");
  StringBuilder ini=new StringBuilder("companion=1\nfullscreen=1\nwidth=1280\nheight=720\nshader_preset=\nmsu_dir="+new File(getFilesDir(),"msu").getAbsolutePath()+"\n");SharedPreferences.Editor prefs=preferences.edit();
  for(Map.Entry<String,CheckBox> item:checks.entrySet()){boolean value=item.getValue().isChecked();prefs.putBoolean(item.getKey(),value);ini.append(item.getKey()).append('=').append(value?1:0).append('\n');}
  for(Map.Entry<String,EditText> item:numbers.entrySet()){int[] bounds=(int[])item.getValue().getTag();int v=Integer.parseInt(item.getValue().getText().toString());if(v<bounds[0]||v>bounds[1])throw new IOException("Invalid setting: "+item.getKey());prefs.putInt(item.getKey(),v);ini.append(item.getKey()).append('=').append(v).append('\n');}prefs.apply();
  byte[] eb=new byte[16];eb[0]='E';eb[1]='B';eb[2]='S';eb[3]='T';eb[4]=5;eb[5]=(byte)preferences.getInt("sprint",1);eb[6]=(byte)(checks.get("hq_audio").isChecked()?1:0);eb[7]=(byte)(checks.get("nintendo_labels").isChecked()?1:0);eb[9]=(byte)(checks.get("scanlines").isChecked()?1:0);eb[10]=(byte)(preferences.getInt("filter",1)==1?1:0);eb[11]=(byte)(checks.get("tilt_shift").isChecked()?1:0);eb[12]=(byte)(checks.get("wide_fov").isChecked()?1:0);eb[13]=(byte)(checks.get("color_grading").isChecked()?1:0);eb[14]=(byte)preferences.getInt("aspect",0);atomic(new File(session,"settings.dat"),eb);atomic(new File(session,"earthbound.ini"),ini.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
  List<String> args=new ArrayList<>(Arrays.asList("--session-dir",session.getAbsolutePath(),"--assets",pack.getAbsolutePath(),"--log-file",new File(session,"game.log").getAbsolutePath()));if(redux)args.add("--allow-redux-development");if(redux&&checks.get("original_title").isChecked()){if(!original.isFile())throw new IOException("Import Original data for its title presentation.");args.add("--original-title-assets");args.add(original.getAbsolutePath());}if(resume)args.add("--load-state");Intent game=new Intent(this,GameActivity.class);game.putExtra("arguments",args.toArray(new String[0]));startActivity(game);
 }
}
