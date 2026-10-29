// SPDX-License-Identifier: GPL-3.0-or-later
package org.earthbound.companion;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.InsetDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.Button;
import android.widget.FrameLayout;
import java.util.ArrayList;

/** Android-only game HUD. Native action IDs and the launcher hide preference stay unchanged. */
public final class TouchControls extends FrameLayout {
 private static final int ACTION_SETTINGS=19;
 private static final int INK=0xfff7f3ff,GOLD=0xfffad870,DARK=0xff12101f;
 private final TouchStick.Actions actions;
 private final ArrayList<ActionButton> buttons=new ArrayList<>();
 private StickView stick;
 private Boolean compact;
 public TouchControls(Context context,TouchStick.Actions actions){
  super(context);this.actions=actions;setMotionEventSplittingEnabled(true);
  setClipChildren(false);setClipToPadding(false);
  setOnApplyWindowInsetsListener((view,insets)->{
   int left,top,right,bottom;
   if(Build.VERSION.SDK_INT>=30){android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());left=safe.left;top=safe.top;right=safe.right;bottom=safe.bottom;}
   else{left=insets.getSystemWindowInsetLeft();top=insets.getSystemWindowInsetTop();right=insets.getSystemWindowInsetRight();bottom=insets.getSystemWindowInsetBottom();}
   setPadding(left+dp(20),top+dp(10),right+dp(20),bottom+dp(18));return insets;
  });
  setPadding(dp(20),dp(10),dp(20),dp(18));
 }
 private int dp(float value){return Math.round(value*getResources().getDisplayMetrics().density);}
 @Override protected void onMeasure(int widthSpec,int heightSpec){
  boolean small=MeasureSpec.getSize(heightSpec)/getResources().getDisplayMetrics().density<500;
  if(compact==null||compact!=small){compact=small;build(small);}
  super.onMeasure(widthSpec,heightSpec);
 }
 private void build(boolean small){
  releaseAll();removeAllViews();buttons.clear();
  stick=new StickView(getContext(),actions);stick.setTag("touch-stick");
  addView(stick,new LayoutParams(dp(small?176:208),dp(small?176:208),Gravity.BOTTOM|Gravity.LEFT));

  int face=small?48:56,gap=8,spacing=face+gap;
  // Short landscape windows put shoulders beside the diamond, keeping them clear of the toolbar.
  int shoulder=small?56:0,width=small?shoulder+2*spacing+face:2*spacing+face+12;
  int top=small?0:48+gap,height=top+2*spacing+face;
  FrameLayout pad=new FrameLayout(getContext());pad.setMotionEventSplittingEnabled(true);
  addView(pad,new LayoutParams(dp(width),dp(height),Gravity.BOTTOM|Gravity.RIGHT));
  addAt(pad,button("L",4,false,false),0,0,small?48:64,48);
  addAt(pad,button("R",5,false,false),small?0:width-64,small?56:0,small?48:64,48);
  int center=small?shoulder+spacing:(width-face)/2;
  addAt(pad,button("X",2,true,false),center,top,face,face);
  addAt(pad,button("Y",3,true,false),center-spacing,top+spacing,face,face);
  addAt(pad,button("A",0,true,true),center+spacing,top+spacing,face,face);
  addAt(pad,button("B",1,true,false),center,top+2*spacing,face,face);

  // Keep the center clear for dialogue and battle menus. Two short edge groups
  // also leave room for the stick and face buttons in landscape windows.
  FrameLayout system=new FrameLayout(getContext());system.setMotionEventSplittingEnabled(true);
  addView(system,new LayoutParams(dp(72),dp(104),Gravity.TOP|Gravity.LEFT));
  addAt(system,utilityButton("Start",6),0,0,72,48);
  addAt(system,utilityButton("Select",7),0,56,72,48);
  FrameLayout tools=new FrameLayout(getContext());tools.setMotionEventSplittingEnabled(true);
  addView(tools,new LayoutParams(dp(120),dp(104),Gravity.TOP|Gravity.RIGHT));
  addAt(tools,utilityButton("Save",13),0,0,56,48);
  addAt(tools,utilityButton("Load",14),0,56,56,48);
  addAt(tools,utilityButton("Fast",12),64,56,56,48);
  ActionButton settings=button("",ACTION_SETTINGS,true,false);settings.setContentDescription("Settings");
  settings.setCompoundDrawablesWithIntrinsicBounds(null,new SettingsIcon(dp(22)),null,null);settings.setPadding(0,dp(13),0,0);
  settings.setBackground(new InsetDrawable(settings.getBackground(),dp(2)));
  addAt(tools,settings,68,0,48,48);
 }
 private ActionButton utilityButton(String label,int action){ActionButton b=button(label,action,false,false);b.setTextSize(13);b.setBackground(new InsetDrawable(b.getBackground(),dp(2)));return b;}
 private void addAt(FrameLayout parent,View child,int x,int y,int w,int h){LayoutParams p=new LayoutParams(dp(w),dp(h));p.leftMargin=dp(x);p.topMargin=dp(y);parent.addView(child,p);}
 private ActionButton button(String label,int action,boolean circle,boolean primary){ActionButton b=new ActionButton(getContext(),label,action,circle,primary);buttons.add(b);return b;}
 public void releaseAll(){if(stick!=null)stick.release();if(buttons!=null)for(ActionButton b:buttons)b.release();}
 @Override protected void onDetachedFromWindow(){releaseAll();super.onDetachedFromWindow();}
 @Override protected void onVisibilityChanged(View view,int visibility){super.onVisibilityChanged(view,visibility);if(visibility!=VISIBLE)releaseAll();}

 private GradientDrawable shape(boolean circle,int fill,int stroke){GradientDrawable d=new GradientDrawable();d.setShape(circle?GradientDrawable.OVAL:GradientDrawable.RECTANGLE);if(!circle)d.setCornerRadius(dp(14));d.setColor(fill);d.setStroke(dp(1),stroke);return d;}
 private final class ActionButton extends Button {
  private final int action;
  private int pointer=-1;
  private boolean pointerDown,a11yDown,sent,touchClick;
  private final Runnable endPulse=()->{a11yDown=false;sync();};
  ActionButton(Context context,String label,int action,boolean circle,boolean primary){
   super(context);this.action=action;setText(label);setTag("touch-action-"+action);
   setContentDescription(action==3?"Y / Run":action==12?"Fast forward":label);
   setAllCaps(false);setTextSize(label.length()>1?14:19);setTypeface(Typeface.DEFAULT,Typeface.BOLD);
   setTextColor(primary?DARK:INK);setMinWidth(0);setMinimumWidth(0);setMinHeight(0);setMinimumHeight(0);setPadding(dp(4),0,dp(4),0);setGravity(Gravity.CENTER);
   StateListDrawable states=new StateListDrawable();
   states.addState(new int[]{android.R.attr.state_pressed},shape(circle,primary?GOLD:0xef3f3759,GOLD));
   states.addState(new int[]{},shape(circle,primary?0xdffad870:0xa612101f,primary?GOLD:0x90c2b6d8));setBackground(states);setStateListAnimator(null);
  }
  private void sync(){boolean down=pointerDown||a11yDown;setPressed(down);if(down!=sent){sent=down;actions.set(action,down);}}
  void release(){pointer=-1;pointerDown=a11yDown=false;removeCallbacks(endPulse);sync();}
  @Override public boolean onTouchEvent(MotionEvent event){
   int kind=event.getActionMasked(),index=event.getActionIndex();
   if(kind==MotionEvent.ACTION_DOWN){release();pointer=event.getPointerId(index);pointerDown=true;sync();getParent().requestDisallowInterceptTouchEvent(true);return true;}
   if(kind==MotionEvent.ACTION_MOVE){int i=event.findPointerIndex(pointer);if(i<0){release();return true;}pointerDown=event.getX(i)>=0&&event.getX(i)<getWidth()&&event.getY(i)>=0&&event.getY(i)<getHeight();sync();return true;}
   if(kind==MotionEvent.ACTION_CANCEL){release();return true;}
   if(kind==MotionEvent.ACTION_UP||kind==MotionEvent.ACTION_POINTER_UP){
    if(event.getPointerId(index)==pointer){boolean click=pointerDown;release();if(click){touchClick=true;performClick();touchClick=false;}}return true;
   }
   return true;
  }
  @Override public boolean performClick(){super.performClick();if(!touchClick){a11yDown=true;sync();removeCallbacks(endPulse);postDelayed(endPulse,100);}return true;}
 }

 public static final class StickView extends View {
  private final TouchStick model;
  private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Path arrow=new Path();
  private final Runnable endPulse;
  public StickView(Context context,TouchStick.Actions actions){
   super(context);model=new TouchStick(actions);endPulse=()->{model.end(Integer.MAX_VALUE);invalidate();};
   setContentDescription("Movement stick. Slide to move in eight directions; release to stop.");setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
  }
  private float radius(){return Math.min(getWidth(),getHeight())*.42f;}
  public void release(){removeCallbacks(endPulse);model.release();invalidate();}
  @Override public boolean onTouchEvent(MotionEvent event){
   int kind=event.getActionMasked(),index=event.getActionIndex();float cx=getWidth()*.5f,cy=getHeight()*.5f,r=radius();
   if(kind==MotionEvent.ACTION_DOWN){
    if(Math.hypot(event.getX(index)-cx,event.getY(index)-cy)>r*1.15f)return false;
    release();model.begin(event.getPointerId(index),event.getX(index)-cx,event.getY(index)-cy,r);getParent().requestDisallowInterceptTouchEvent(true);
   }else if(kind==MotionEvent.ACTION_MOVE){int i=event.findPointerIndex(model.pointer());if(i<0)release();else model.move(model.pointer(),event.getX(i)-cx,event.getY(i)-cy,r);}
   else if(kind==MotionEvent.ACTION_UP||kind==MotionEvent.ACTION_POINTER_UP)model.end(event.getPointerId(index));
   else if(kind==MotionEvent.ACTION_CANCEL)release();
   invalidate();return true;
  }
  @Override protected void onDraw(Canvas canvas){
   super.onDraw(canvas);float cx=getWidth()*.5f,cy=getHeight()*.5f,r=radius(),line=getResources().getDisplayMetrics().density;
   paint.setStyle(Paint.Style.FILL);paint.setColor(0x5512101f);canvas.drawCircle(cx,cy,r,paint);
   paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.5f*line);paint.setColor(model.pointer()<0?0x85c2b6d8:0xbffad870);canvas.drawCircle(cx,cy,r,paint);
   paint.setColor(0x38c2b6d8);canvas.drawCircle(cx,cy,r*.67f,paint);
   int[] bits={TouchStick.UP,TouchStick.RIGHT,TouchStick.DOWN,TouchStick.LEFT};
   for(int i=0;i<4;i++){
    canvas.save();canvas.rotate(i*90,cx,cy);paint.setStyle(Paint.Style.FILL);paint.setColor((model.mask()&bits[i])!=0?GOLD:0xb3f7f3ff);
    arrow.reset();arrow.moveTo(cx,cy-r*.83f);arrow.lineTo(cx-r*.075f,cy-r*.70f);arrow.lineTo(cx+r*.075f,cy-r*.70f);arrow.close();canvas.drawPath(arrow,paint);canvas.restore();
   }
   float tx=cx+model.x()*r*.60f,ty=cy+model.y()*r*.60f;
   paint.setStyle(Paint.Style.FILL);paint.setColor(model.pointer()<0?0xc52a263e:GOLD);canvas.drawCircle(tx,ty,r*.31f,paint);
   paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.5f*line);paint.setColor(model.pointer()<0?0xc2f7f3ff:0xff1a182a);canvas.drawCircle(tx,ty,r*.31f,paint);
  }
  @Override public void onInitializeAccessibilityNodeInfo(AccessibilityNodeInfo info){super.onInitializeAccessibilityNodeInfo(info);info.setScrollable(true);info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_UP);info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_DOWN);info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_LEFT);info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_RIGHT);}
  @Override public boolean performAccessibilityAction(int action,Bundle arguments){
   float dx=0,dy=0;
   if(action==AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_UP.getId())dy=-1;
   else if(action==AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_DOWN.getId())dy=1;
   else if(action==AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_LEFT.getId())dx=-1;
   else if(action==AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_RIGHT.getId())dx=1;
   else return super.performAccessibilityAction(action,arguments);
   if(model.pointer()>=0&&model.pointer()!=Integer.MAX_VALUE)return false;
   release();model.begin(Integer.MAX_VALUE,dx,dy,1);postDelayed(endPulse,100);invalidate();return true;
  }
 }
 private static final class SettingsIcon extends Drawable {
  private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);private final int size;
  SettingsIcon(int size){this.size=size;setBounds(0,0,size,size);}
  @Override public int getIntrinsicWidth(){return size;}
  @Override public int getIntrinsicHeight(){return size;}
  @Override public void draw(Canvas canvas){paint.setColor(INK);paint.setStrokeWidth(size*.075f);paint.setStrokeCap(Paint.Cap.ROUND);for(int i=0;i<3;i++){float y=size*(.23f+i*.27f),x=size*(i==1?.65f:.35f);canvas.drawLine(size*.1f,y,size*.9f,y,paint);paint.setStyle(Paint.Style.FILL);paint.setColor(DARK);canvas.drawCircle(x,y,size*.1f,paint);paint.setStyle(Paint.Style.STROKE);paint.setColor(INK);canvas.drawCircle(x,y,size*.1f,paint);paint.setStyle(Paint.Style.FILL);}}
  @Override public void setAlpha(int alpha){paint.setAlpha(alpha);}
  @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);}
  @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
 }
}
