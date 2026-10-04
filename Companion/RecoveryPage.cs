namespace EarthBoundCompanion;

sealed partial class MainForm {
 void BackupSession(string session) {
  if(Running||generating){Notify("Close the game before making a recovery backup.",true);return;}
  Try(()=>Notify("Backup created: "+Path.GetFileName(Settings.Backup(true,session))));
 }
 void RestoreSession(string session) {
  if(Running||generating){Notify("Close the game before restoring saves.",true);return;}
  using var dialog=new OpenFileDialog {Filter="Companion save backup (*.zip)|*.zip",InitialDirectory=Path.Combine(Settings.User,"Backups"),Title="Restore matching adventure backup"};
  if(dialog.ShowDialog(this)!=DialogResult.OK)return;
  using var form=new Form {Text="Restore saves",BackColor=Theme.Canvas,ForeColor=Theme.Ink,Font=Theme.Font(),ClientSize=new Size(540,225),FormBorderStyle=FormBorderStyle.FixedDialog,MaximizeBox=false,MinimizeBox=false,StartPosition=FormStartPosition.CenterParent};
  var text=Theme.Text("Restore the selected backup into this adventure. Your current saves will be backed up first. Other adventures and settings stay as they are.",11);text.Location=new Point(22,18);text.MaximumSize=new Size(495,0);form.Controls.Add(text);
  var phone=new CheckBox {Text="Phone saves only (portable across engine builds)",Checked=true,AutoSize=true,ForeColor=Theme.Ink,Location=new Point(22,103)};form.Controls.Add(phone);
  var restore=Theme.Button("Restore backup",()=>form.DialogResult=DialogResult.OK,true);restore.Location=new Point(22,160);form.Controls.Add(restore);
  var cancel=Theme.Button("Cancel",()=>form.DialogResult=DialogResult.Cancel);cancel.Location=new Point(230,160);form.Controls.Add(cancel);form.CancelButton=cancel;
  if(form.ShowDialog(this)!=DialogResult.OK)return;
  Try(()=>{var result=SaveRecovery.Restore(dialog.FileName,session,phone.Checked);ShowPage(current);Notify($"Restored {result.Files} save file(s). Previous saves: {Path.GetFileName(result.PreviousBackup)}");});
 }
}
