@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.provider.MediaStore
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.remote.*
import com.example.data.model.TelecomPackage
import com.example.data.model.WalletAccount
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private val V2Bg = Color(0xFFF4F2F5)
private val V2Text = Color(0xFF1B2230)
private val V2Muted = Color(0xFF7E8590)
private val V2Pink = Color(0xFFB20B4C)
private val V2Peach = Color(0xFFFFE0B2)
private val V2Green = Color(0xFF2E8B57)
private val V2Red = Color(0xFFC83D47)

private enum class V2Action { BALANCE, INSTANT, PACKAGES, WHOLESALE, RIYAL }
private data class V2Provider(val title: String, val color: Color, val mark: String)

private fun v2Digits(value: String): String = buildString(value.length) { value.forEach { ch -> append(when (ch) {
    '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4'; '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9'
    '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4'; '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9'
    else -> ch
}) } }
private fun v2Phone(v: String): String = v2Digits(v).filter(Char::isDigit).removePrefix("00967").removePrefix("967")
private fun v2Money(v: Double?): String = v?.let { if (it % 1.0 == 0.0) it.toInt().toString() else String.format("%.2f", it) } ?: "—"
private fun v2Num(result: Map<String, Any?>, keys: Set<String>): Double? { fun walk(v: Any?): Double? = when (v) {
    is Map<*, *> -> v.entries.firstNotNullOfOrNull { (k, x) -> { val n = k.toString().lowercase().replace("_", "").replace(" ", ""); if (keys.any(n::contains)) x?.toString()?.toDoubleOrNull() else walk(x) } }
    is List<*> -> v.firstNotNullOfOrNull(::walk)
    else -> null
}; return walk(result) }
private fun v2Text(result: Map<String, Any?>, keys: Set<String>): String? { fun walk(v: Any?): String? = when (v) {
    is Map<*, *> -> v.entries.firstNotNullOfOrNull { (k, x) -> { val n = k.toString().lowercase().replace("_", "").replace(" ", ""); if (keys.any(n::contains) && x !is Map<*, *> && x !is List<*>) x?.toString() else walk(x) } }
    is List<*> -> v.firstNotNullOfOrNull(::walk)
    else -> null
}; return walk(result) }
private fun v2Provider(phone: String) = if (v2Phone(phone).startsWith("77") || v2Phone(phone).startsWith("78")) V2Provider("يمن موبايل", V2Pink, "YM") else V2Provider("شبكة السداد", V2Pink, "K")

private fun v2Flatten(catalog: List<ServiceMainCategoryDto>): List<ServiceDto> = catalog.flatMap { m -> m.categories.flatMap { root -> fun walk(c: ServiceCategoryDto): List<ServiceDto> = c.services + c.children.flatMap(::walk); walk(root) } }.distinctBy { it.id }
private fun v2Setting(settings: List<ServiceSettingDto>, services: List<ServiceDto>, key: String): ServiceDto? { val s = settings.firstOrNull { it.key == key && it.isConfigured } ?: return null; val id = s.serviceId ?: s.service?.id ?: return null; return services.firstOrNull { it.id == id } }
private fun v2FieldValue(field: ServiceFieldDto, phone: String, amount: String): String? { val k = field.key.lowercase().replace("_", "").replace("-", ""); return when {
    k in setOf("mobile", "phone", "phonenumber", "msisdn", "mobilenumber", "recipient", "targetmobile") || field.label.contains("هاتف") || field.label.contains("جوال") -> v2Phone(phone)
    k in setOf("amount", "value", "price") || field.label.contains("المبلغ") -> amount.takeIf(String::isNotBlank)
    field.type.equals("select", true) -> field.choices.firstOrNull()
    else -> null
} }
private fun v2Payload(service: ServiceDto, phone: String, amount: String): Map<String,String?> = service.fields.associate { it.key to v2FieldValue(it, phone, amount) }

private suspend fun v2SubmitAndPoll(baseUrl: String, token: String, service: ServiceDto, phone: String, amount: String, item: ServiceItemDto? = null): ServiceTransactionDto {
    val key = UUID.randomUUID().toString(); val payload = v2Payload(service, phone, amount)
    val missing = service.fields.firstOrNull { it.required && payload[it.key].isNullOrBlank() && item == null }
    if (missing != null) error("الحقل المطلوب: ${missing.label}")
    val api = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/")
    val r = api.submitServiceRequest("Token $token", key, ServiceRequestPayload(service.id, item?.type, item?.id, payload, key))
    if (!r.isSuccessful || r.body() == null) error("تعذر تنفيذ العملية (HTTP ${r.code()})")
    var tx = r.body()!!
    repeat(30) { if (tx.status in setOf("success", "failed", "refunded", "manual_review") || tx.result.isNotEmpty()) return tx; delay(850); api.getServiceTransaction("Token $token", tx.id).body()?.let { tx = it } }
    return tx
}

private fun v2Download(context: Context, tx: ServiceTransactionDto): Boolean {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false
    return runCatching {
        val values = ContentValues().apply { put(MediaStore.Downloads.DISPLAY_NAME, "katolin-${tx.id.takeLast(12)}.txt"); put(MediaStore.Downloads.MIME_TYPE, "text/plain"); put(MediaStore.Downloads.RELATIVE_PATH, "Download/Katolin") }
        val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return false
        context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use { out -> out.appendLine("كاتولين - إيصال عملية"); out.appendLine("الحالة: ${tx.status}"); out.appendLine("المرجع: ${tx.id}"); tx.amount?.let { out.appendLine("المبلغ: $it ${tx.currency.orEmpty()}") }; tx.providerTransactionId?.let { out.appendLine("معرف المزود: $it") }; tx.result.entries.forEach { (k,v) -> out.appendLine("$k: $v") } } ?: return false
        true
    }.getOrDefault(false)
}

@Composable private fun V2Header(provider: V2Provider, onRefresh: () -> Unit, onBack: () -> Unit) = TopAppBar(
    title = { Column(horizontalAlignment = Alignment.CenterHorizontally) { Text("رصيدي", color = Color.White, fontWeight = FontWeight.Black, fontSize = 19.sp); Text("****** • رصيد مخفي", color = Color.White.copy(.9f), fontSize = 9.sp, fontWeight = FontWeight.Bold) } },
    navigationIcon = { IconButton(onClick = onRefresh) { Icon(Icons.Default.Refresh, null, tint = Color.White) } },
    actions = { IconButton(onClick = onBack) { Icon(Icons.Default.Settings, null, tint = Color.White) } },
    colors = TopAppBarDefaults.topAppBarColors(containerColor = provider.color)
)

@Composable private fun V2PhoneCard(phone: String, onPhoneChange: (String) -> Unit, provider: V2Provider) = Card(Modifier.fillMaxWidth(), RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Surface(Modifier.size(52.dp), CircleShape, provider.color.copy(.1f)) { Box(contentAlignment = Alignment.Center) { Text(provider.mark, color = provider.color, fontWeight = FontWeight.Black) } }; Spacer(Modifier.width(10.dp)); Column(Modifier.weight(1f), horizontalAlignment = Alignment.End) { Text(provider.title, color = provider.color, fontWeight = FontWeight.Black, fontSize = 21.sp); Text("خدمة السداد", color = V2Muted, fontSize = 9.sp) } }
        OutlinedTextField(phone, onPhoneChange, Modifier.fillMaxWidth(), singleLine = true, label = { Text("رقم الهاتف") }, leadingIcon = { Icon(Icons.Default.Call, null, tint = provider.color) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), shape = RoundedCornerShape(11.dp))
    }
}

@Composable private fun V2Tabs(provider: V2Provider, action: V2Action, onSelect: (V2Action) -> Unit) = Surface(Modifier.fillMaxWidth(), RoundedCornerShape(15.dp), provider.color.copy(.10f)) { Row(Modifier.fillMaxWidth().padding(3.dp), horizontalArrangement = Arrangement.spacedBy(2.dp)) { listOf(V2Action.BALANCE to "رصيد", V2Action.INSTANT to "فوري", V2Action.PACKAGES to "باقات", V2Action.WHOLESALE to "جملة", V2Action.RIYAL to "ريال").forEach { (a,label) -> Box(Modifier.weight(1f).clickable { onSelect(a) }, contentAlignment = Alignment.Center) { Surface(RoundedCornerShape(11.dp), if (action == a) provider.color else Color.Transparent) { Text(label, color = if (action == a) Color.White else V2Text, fontWeight = FontWeight.Black, fontSize = 11.sp, modifier = Modifier.padding(vertical=9.dp, horizontal=4.dp)) } } } } }

@Composable private fun V2InfoCard(provider: V2Provider, balanceTx: ServiceTransactionDto?, advanceTx: ServiceTransactionDto?) = Card(Modifier.fillMaxWidth(), RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(Color.White)) {
    val b=v2Num(balanceTx?.result.orEmpty(), setOf("balance","availablebalance","availablecredit","rasid")); val l=v2Num(advanceTx?.result.orEmpty(), setOf("loan","sulfa","loanamount","sulfaamount")); val t=v2Text(balanceTx?.result.orEmpty(), setOf("mobiletype","mobiltype","linetype","type"))
    Column(Modifier.padding(12.dp), verticalArrangement=Arrangement.spacedBy(9.dp)) { Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween) { Text("بيانات الرقم", color=provider.color, fontWeight=FontWeight.Black); Text("✓", color=V2Green, fontWeight=FontWeight.Black) }; Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceEvenly) { Column(horizontalAlignment=Alignment.CenterHorizontally) { Text(v2Money(b), color=provider.color, fontWeight=FontWeight.Black, fontSize=20.sp); Text("رصيد الرقم", color=V2Muted, fontSize=9.sp) }; Column(horizontalAlignment=Alignment.CenterHorizontally) { Text(t ?: "—", color=V2Text, fontWeight=FontWeight.Black, fontSize=12.sp); Text("نوع الرقم", color=V2Muted, fontSize=9.sp) }; Column(horizontalAlignment=Alignment.CenterHorizontally) { Text(if((l?:0.0)>0) v2Money(l) else "غير متسلف", color=if((l?:0.0)>0)V2Red else V2Green, fontWeight=FontWeight.Black, fontSize=12.sp); Text("فحص السلفة", color=V2Muted, fontSize=9.sp) } } }
}

@Composable private fun V2PackageCard(item: ServiceItemDto, provider: V2Provider, onClick: () -> Unit) {
    val md=item.metadata; fun meta(vararg k:String)=k.firstNotNullOfOrNull{md[it]?:md[it.lowercase()]}; val payment=meta("payment_type","paymentType")?:"دفع مسبق"; val line=meta("line_type","lineType","line")?:"شريحة"; val quota=meta("quota","data"); val days=meta("validity_days","days","duration")
    Card(Modifier.fillMaxWidth().clickable(onClick=onClick), RoundedCornerShape(16.dp), colors=CardDefaults.cardColors(V2Peach)) { Column(Modifier.padding(12.dp), verticalArrangement=Arrangement.spacedBy(7.dp)) { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.Top) { Surface(RoundedCornerShape(13.dp),Color.White,Modifier.size(58.dp)){Box(contentAlignment=Alignment.Center){Text(provider.mark,color=provider.color,fontWeight=FontWeight.Black)}}; Column(Modifier.weight(1f).padding(horizontal=10.dp),horizontalAlignment=Alignment.End){Text(item.name,color=provider.color,fontWeight=FontWeight.Black,fontSize=15.sp);Text("$payment • $line",color=V2Text,fontSize=10.sp,fontWeight=FontWeight.Bold)} }; Text(item.price?.toDoubleOrNull()?.let(::v2Money)?:"—",color=V2Text,fontWeight=FontWeight.Black,fontSize=34.sp,modifier=Modifier.fillMaxWidth(),textAlign=TextAlign.Center); Button(onClick=onClick,modifier=Modifier.fillMaxWidth().height(42.dp),colors=ButtonDefaults.buttonColors(containerColor=provider.color),shape=RoundedCornerShape(11.dp)){Text("تجديد / تفعيل",fontWeight=FontWeight.Black)}; Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceEvenly){days?.let{Text("⏱ $it",color=V2Muted,fontSize=9.sp)};quota?.let{Text("◉ $it",color=V2Muted,fontSize=9.sp)}} } }
}

@Composable private fun V2PackageTree(provider: V2Provider, catalogService: ServiceDto?, purchaseService: ServiceDto?, onSelect:(ServiceItemDto)->Unit){ val items=(catalogService?.items.orEmpty()+purchaseService?.items.orEmpty()).filter{it.type=="telecom_plans"}.distinctBy{it.id}; val byId=items.associateBy{it.id}; val types=catalogService?.planTypes.orEmpty().ifEmpty{purchaseService?.planTypes.orEmpty()}; val groups=if(types.isNotEmpty()) types.mapNotNull{t->val x=t.planIds.mapNotNull(byId::get); if(x.isNotEmpty())t.name to x else null}else items.groupBy{(it.metadata["payment_type"]?:"")+" - "+(it.metadata["line_type"]?:"")}.toList(); var expanded by remember(groups){mutableStateOf(groups.firstOrNull()?.first)}; Column(verticalArrangement=Arrangement.spacedBy(7.dp)){groups.forEach{(title,list)->Surface(Modifier.fillMaxWidth().clickable{expanded=if(expanded==title)null else title},RoundedCornerShape(13.dp),provider.color.copy(.09f)){Row(Modifier.fillMaxWidth().padding(12.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(if(expanded==title)"⌃" else "⌄",color=provider.color);Text(title,color=provider.color,fontWeight=FontWeight.Black,fontSize=13.sp,modifier=Modifier.weight(1f),textAlign=TextAlign.End)}};if(expanded==title)list.forEach{V2PackageCard(it,provider){onSelect(it)}}};if(groups.isEmpty())Text("لا توجد باقات متاحة حاليًا.",color=V2Muted,modifier=Modifier.fillMaxWidth().padding(15.dp),textAlign=TextAlign.Center)}}

@Composable fun PaymentNetworkScreen(
    wallet: WalletAccount, packages: List<TelecomPackage>, formatMoney:(Double)->String, onBackClick:()->Unit, onSyncBalance:()->Unit, onRechargeSubmit:(String,String,String,String,Double)->Unit, modifier:Modifier=Modifier
){
    val repo=remember{StoreRepository.instance}; val baseUrl by repo.djangoBaseUrl.collectAsState(); val session by repo.userSession.collectAsState(); val scope=rememberCoroutineScope(); val provider=v2Provider(session.phone)
    var phone by remember(session.phone){mutableStateOf(session.phone)}; var catalog by remember{mutableStateOf(emptyList<ServiceMainCategoryDto>())}; var settings by remember{mutableStateOf(emptyList<ServiceSettingDto>())}; var action by remember{mutableStateOf(V2Action.BALANCE)}
    var balanceTx by remember{mutableStateOf<ServiceTransactionDto?>(null)}; var advanceTx by remember{mutableStateOf<ServiceTransactionDto?>(null)}; var packageTx by remember{mutableStateOf<ServiceTransactionDto?>(null)}; var selectedItem by remember{mutableStateOf<ServiceItemDto?>(null)}; var selectedService by remember{mutableStateOf<ServiceDto?>(null)}; var operationTx by remember{mutableStateOf<ServiceTransactionDto?>(null)}; var amount by remember{mutableStateOf("")}; var loading by remember{mutableStateOf(false)}; var refreshing by remember{mutableStateOf(false)}; var duplicateCount by remember{mutableStateOf(0)}; var showDuplicate by remember{mutableStateOf(false)}; var showConfirm by remember{mutableStateOf(false)}; var error by remember{mutableStateOf<String?>(null)}; var downloaded by remember{mutableStateOf(false)}
    val services=remember(catalog){v2Flatten(catalog)}; fun s(key:String)=v2Setting(settings,services,key); val balanceQuery=s("yemen_mobile_balance_query"); val advanceQuery=s("yemen_mobile_advance_query"); val packagesQuery=s("yemen_mobile_packages_query"); val packagesList=s("yemen_mobile_packages_list"); val denominations=s("yemen_mobile_denominations_list"); val recharge=s("yemen_mobile_recharge"); val packagePay=s("yemen_mobile_package_pay_activate")?:s("yemen_mobile_package_activate")
    fun refresh(){val token=session.token?:run{error="سجل الدخول أولًا.";return};scope.launch{refreshing=true;error=null;runCatching{val api=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/");catalog=api.getServiceCatalog("Token $token").body()?.categories ?: throw IllegalStateException("تعذر جلب الكتالوج");settings=api.getServiceSettings("Token $token",group="yemen_mobile",configured="1").body()?.settings.orEmpty()}.onFailure{error=it.localizedMessage?:"تعذر تحديث الخدمات"};refreshing=false}}
    LaunchedEffect(baseUrl,session.token){if(session.token!=null)refresh()}
    fun queryPackages(){val token=session.token?:return;val p=packagesQuery?:run{error="خدمة استعلام الباقات غير مهيأة.";return};scope.launch{loading=true;error=null;runCatching{listOfNotNull(balanceQuery?.let{async{v2SubmitAndPoll(baseUrl,token,it,phone,"")}},advanceQuery?.let{async{v2SubmitAndPoll(baseUrl,token,it,phone,"")}},async{v2SubmitAndPoll(baseUrl,token,p,phone,"")}).awaitAll().let{xs->balanceTx=xs.firstOrNull{it.service==balanceQuery?.code};advanceTx=xs.firstOrNull{it.service==advanceQuery?.code};packageTx=xs.firstOrNull{it.service==p.code}}}.onFailure{error=it.localizedMessage?:"تعذر استعلام الباقات"};loading=false}}
    fun queryBalance(){val token=session.token?:return;val b=balanceQuery?:run{error="خدمة استعلام الرصيد غير مهيأة.";return};scope.launch{loading=true;runCatching{balanceTx=v2SubmitAndPoll(baseUrl,token,b,phone,"");advanceTx=advanceQuery?.let{v2SubmitAndPoll(baseUrl,token,it,phone,"")}}.onFailure{error=it.localizedMessage?:"تعذر الاستعلام"};loading=false}}
    fun preparePurchase(item:ServiceItemDto?,service:ServiceDto?){val token=session.token?:return;val target=service?:selectedService?:run{error="خدمة التسديد غير مهيأة من الإعدادات الأساسية.";return};selectedItem=item;selectedService=target;loading=true;scope.launch{runCatching{val r=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/").getServiceReports("Token $token",mobile=v2Phone(phone),today="1",service=target.code);duplicateCount=if(r.isSuccessful)r.body()?.results.orEmpty().size else 0;if(duplicateCount>0)showDuplicate=true else showConfirm=true}.onFailure{showConfirm=true};loading=false}}
    fun purchase(){val token=session.token?:return;val service=selectedService?:return;scope.launch{loading=true;error=null;runCatching{operationTx=v2SubmitAndPoll(baseUrl,token,service,phone,amount,selectedItem);showConfirm=false;downloaded=false;if(operationTx?.status=="success"){onSyncBalance();onRechargeSubmit(phone,provider.title,service.name,selectedItem?.name?:service.name,operationTx?.amount?.toDoubleOrNull()?:amount.toDoubleOrNull()?:0.0)}}.onFailure{error=it.localizedMessage?:"تعذر تنفيذ التسديد"};loading=false}}
    Scaffold(modifier.fillMaxSize(),topBar={V2Header(provider,::refresh,onBackClick)}){pad->LazyColumn(Modifier.fillMaxSize().padding(pad).background(V2Bg),contentPadding=PaddingValues(10.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
        item{V2PhoneCard(phone,{phone=it},provider)};item{V2Tabs(provider,action){action=it;if(it==V2Action.PACKAGES)queryPackages()}}
        if(action==V2Action.BALANCE){item{V2InfoCard(provider,balanceTx,advanceTx)};item{Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(7.dp)){Button(onClick=::queryBalance,Modifier.weight(1f).height(48.dp),colors=ButtonDefaults.buttonColors(containerColor=provider.color),shape=RoundedCornerShape(12.dp)){Text("استعلام",fontWeight=FontWeight.Black)};Button(onClick={preparePurchase(null,recharge)},Modifier.weight(1f).height(48.dp),colors=ButtonDefaults.buttonColors(containerColor=V2Peach),shape=RoundedCornerShape(12.dp)){Text("تسديد",color=provider.color,fontWeight=FontWeight.Black)}}}}
        if(action==V2Action.PACKAGES){item{V2InfoCard(provider,balanceTx,advanceTx)};item{Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("prepaid" to "دفع مسبق","postpaid" to "فوترة","شريحة" to "شريحة","برمجة" to "برمجة","4G" to "4G").forEach{(n,l)->if(packagesList?.items.orEmpty().any{it.metadata.values.any{v->v.contains(n,true)}})Surface(RoundedCornerShape(10.dp),provider.color.copy(.09f)){Text(l,color=provider.color,fontWeight=FontWeight.Black,fontSize=10.sp,modifier=Modifier.padding(9.dp))}}}};item{V2PackageTree(provider,packagesList,packagePay){preparePurchase(it,packagePay)}};item{Button(onClick=::queryPackages,Modifier.fillMaxWidth().height(44.dp),colors=ButtonDefaults.buttonColors(containerColor=provider.color),shape=RoundedCornerShape(11.dp)){Text("تحديث البيانات",fontWeight=FontWeight.Black)}}}
        if(action==V2Action.INSTANT){denominations?.items.orEmpty().filter{it.type.contains("denomination",true)}.take(40).forEach{item{Card(Modifier.fillMaxWidth().clickable{preparePurchase(it,denominations)},RoundedCornerShape(14.dp),colors=CardDefaults.cardColors(V2Peach)){Row(Modifier.fillMaxWidth().padding(13.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Text(it.price?.toDoubleOrNull()?.let(::v2Money)?:"—",fontWeight=FontWeight.Black,fontSize=26.sp,modifier=Modifier.width(80.dp),textAlign=TextAlign.Center);Column(Modifier.weight(1f),horizontalAlignment=Alignment.End){Text(it.name,color=provider.color,fontWeight=FontWeight.Black);Text("بطاقة شحن",color=V2Muted,fontSize=9.sp)};Text(provider.mark,color=provider.color,fontWeight=FontWeight.Black)}}}}}
        if(action==V2Action.WHOLESALE||action==V2Action.RIYAL)item{OutlinedTextField(amount,{amount=it},Modifier.fillMaxWidth(),label={Text("المبلغ")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number),shape=RoundedCornerShape(11.dp))}
        error?.let{msg->item{Text(msg,color=V2Red,modifier=Modifier.fillMaxWidth().padding(10.dp),textAlign=TextAlign.Center,fontWeight=FontWeight.Bold)}};if(loading||refreshing)item{Box(Modifier.fillMaxWidth().padding(12.dp),contentAlignment=Alignment.Center){CircularProgressIndicator(color=provider.color)}}
    }}
    if(showDuplicate)AlertDialog(onDismissRequest={showDuplicate=false},title={Text("تنبيه: يوجد تسديد اليوم",fontWeight=FontWeight.Black,color=provider.color)},text={Text("تم العثور على $duplicateCount عملية لهذا الرقم اليوم. هل تريد التسديد مرة أخرى؟")},confirmButton={Button(onClick={showDuplicate=false;showConfirm=true},colors=ButtonDefaults.buttonColors(containerColor=provider.color)){Text("تسديد مرة أخرى")}},dismissButton={TextButton(onClick={showDuplicate=false}){Text("إلغاء")}})
    if(showConfirm)AlertDialog(onDismissRequest={showConfirm=false},title={Text("تأكيد التسديد",fontWeight=FontWeight.Black)},text={Column(verticalArrangement=Arrangement.spacedBy(5.dp)){Text(selectedItem?.name?:selectedService?.name.orEmpty(),fontWeight=FontWeight.Black);Text("المبلغ: ${selectedItem?.price?:amount} ر.ي")}},confirmButton={Button(onClick=::purchase,colors=ButtonDefaults.buttonColors(containerColor=provider.color)){Text("تأكيد")}},dismissButton={TextButton(onClick={showConfirm=false}){Text("إلغاء")}})
    operationTx?.let{tx->val context=LocalContext.current;AlertDialog(onDismissRequest={operationTx=null},title={Text("نتيجة العملية",fontWeight=FontWeight.Black)},text={Text(if(tx.status=="success")"تمت العملية بنجاح ✅" else tx.errorMessage?:"تعذر تنفيذ العملية")},confirmButton={Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){Button(onClick={downloaded=v2Download(context,tx)},colors=ButtonDefaults.buttonColors(containerColor=provider.color)){Text(if(downloaded)"تم التحميل ✓" else "تحميل")};TextButton(onClick={operationTx=null}){Text("إغلاق")}}})}
}
