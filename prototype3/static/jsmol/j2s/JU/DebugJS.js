Clazz.declarePackage("JU");
(function(){
var c$ = Clazz.declareType(JU, "DebugJS", null);
c$._ = Clazz.defineMethod(c$, "_", 
function(msg){
{
if (Clazz._debugging) {
debugger;
}
}}, "~S");
})();
;//5.0.1-v7 Wed Apr 02 04:50:42 CDT 2025
