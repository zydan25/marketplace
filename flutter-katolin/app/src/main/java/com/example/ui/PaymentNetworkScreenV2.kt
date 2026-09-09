@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.provider.MediaStore
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Wallet
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
import com.example.data.model.TelecomPackage
import com.example.data.model.WalletAccount
import com.example.data.remote.*
import com.example.data.repository.PaymentSnapshotCache
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

private val Bg = Color(0xFFF4F3F6)
private val TextDark = Color(0xFF1B2230)
private val Muted = Color(0xFF7D8490)
private val White = Color.White
private val Green = Color(0xFF2E8B57)
private val Red = Color(0xFFC83D47)
private val YmPink = Color(0xFFB20B4C)
private val SabaBlue = Color(0xFF1877A7)
private val YouYellow = Color(0xFFE4B400)
private val WhyPurple = Color(0xFF52368A)
private val G4Blue = Color(0xFF1180AF)
private val YNBlue = Color(0xFF3D3289)

private enum class Action { BALANCE, INSTANT, PACKAGES, WHOLESALE, RIYAL }
private data class Provider(val key: String, val title: String, val color: Color, val mark: String)
private data class CachedState(
    val catalog: ServiceCatalogResponse? = null,
    val settings: ServiceSettingsResponse? = null,
    val balance: ServiceTransactionDto? = null,
    val advance: ServiceTransactionDto? = null,
    val offers: ServiceTransactionDto? = null,
    val reports: ServiceTransactionListResponse? = null,
    val lastSync: Long? = null
)

private fun digits(v: String): String = buildString(v.length) { v.forEach { c -> append(when(c) {
    '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4'; '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9'
    '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4'; '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9'
    else -> c
}) } }
private fun phone(v: String): String = digits(v).filter(Char::isDigit).let { when { it.startsWith("00967") -> it.drop(5); it.startsWith("967") -> it.drop(3); else -> it } }
private fun money(v: Double?): String = v?.let { if (it % 1.0 == 0.0) it.toInt().toString() else String.format(Locale.US, "%.2f", it) } ?: "—"
private fun provider(v: String): Provider { val p = phone(v); return when {
    p.startsWith("77") || p.startsWith("78") -> Provider("yemen-mobile", "يمن موبايل", YmPink, "YM")
    p.startsWith("71") -> Provider("sabafon", "سبأفون", SabaBlue, "S")
    p.startsWith("73") -> Provider("you", "YOU", YouYellow, "YOU")
    p.startsWith("70") -> Provider("why", "WHY", WhyPurple, "WHY")
    p.startsWith("10") -> Provider("yemen-4g", "يمن فورجي", G4Blue, "4G")
    p.startsWith("0") -> Provider("yemen-net", "يمن نت", YNBlue, "YN")
    else -> Provider("unknown", "شبكة السداد", YmPink, "K")
} }
private fun flatten(categories: List<ServiceMainCategoryDto>): List<ServiceDto> = categories.flatMap { main -> main.categories.flatMap { root ->
    fun walk(c: ServiceCategoryDto): List<ServiceDto> = c.services + c.children.flatMap(::walk)
    walk(root)
} }.distinctBy { it.id }
private fun norm(v: String): String = v.lowercase().replace(Regex("[^\\p{L}\\p{Nd}]+"), " ").trim()
private fun settingService(settings: List<ServiceSettingDto>, services: List<ServiceDto>, provider: Provider, vararg tokens: String): ServiceDto? {
    val configured = settings.filter { it.isConfigured && (it.serviceId != null || it.service?.id != null) }
    val candidates = configured.mapNotNull { s ->
        val id = s.serviceId ?: s.service?.id ?: return@mapNotNull null
        val service = services.firstOrNull { it.id == id } ?: return@mapNotNull null
        s to service
    }
    val providerTokens = listOf(provider.key, provider.title, provider.key.replace("-", "_"))
    return candidates.map { (s, service) ->
        val hay = norm("${s.key} ${s.name} ${s.group} ${s.description} ${service.code} ${service.name} ${service.serviceKind} ${service.description}")
        val score = tokens.sumOf { if (hay.contains(norm(it))) 4 else 0 } + providerTokens.sumOf { if (hay.contains(norm(it))) 2 else 0 }
        score to service
    }.filter { it.first > 0 }.sortedByDescending { it.first }.firstOrNull()?.second
}
private fun byCode(services: List<ServiceDto>, vararg codes: String): ServiceDto? = codes.firstNotNullOfOrNull { c -> services.firstOrNull { it.code.equals(c, true) } }
private fun resolve(settings: List<ServiceSettingDto>, services: List<ServiceDto>, p: Provider, action: Action, purchase: Boolean): ServiceDto? {
    if (p.key == "yemen-mobile") {
        val key = when {
            !purchase && action == Action.BALANCE -> "yemen_mobile_balance_query"
            !purchase && action == Action.PACKAGES -> "yemen_mobile_packages_query"
            purchase && action == Action.BALANCE -> "yemen_mobile_recharge"
            purchase && action == Action.INSTANT -> "yemen_mobile_denominations_list"
            purchase && action == Action.PACKAGES -> "yemen_mobile_package_pay_activate"
            purchase && action == Action.WHOLESALE -> "mobile_gomla"
            else -> null
        }
        key?.let { settingService(settings, services, p, it) }?.let { return it }
    }
    val text = when (action) {
        Action.BALANCE -> listOf("balance", "رصيد", "query")
        Action.INSTANT -> listOf("denomination", "فئات", "شحن", "instant")
        Action.PACKAGES -> listOf("offer", "package", "باقات")
        Action.WHOLESALE -> listOf("gomla", "wholesale", "جملة")
        Action.RIYAL -> listOf("riy", "open", "balance", "رصيد")
    }
    settingService(settings, services, p, *(text + if (p.key == "yemen-net") listOf("post", "adsl") else emptyList()).toTypedArray())?.let { return it }
    return when (p.key) {
        "yemen-mobile" -> when (action) {
            Action.BALANCE -> byCode(services, if (purchase) "yem-balance" else "yem-query-balance")
            Action.INSTANT -> byCode(services, "yem-denomination")
            Action.PACKAGES -> byCode(services, if (purchase) "yem-offer-bill" else "yem-offer", "yem-bill-offer", "yem-offer")
            Action.WHOLESALE -> byCode(services, "mobile-gomla")
            Action.RIYAL -> byCode(services, "yem-balance")
        }
        "sabafon" -> when (action) {
            Action.BALANCE -> byCode(services, "saba-units")
            Action.INSTANT -> byCode(services, "saba-denomination", "sbay-denomination")
            Action.PACKAGES -> byCode(services, "saba-offer", "sbay-offer")
            Action.WHOLESALE -> byCode(services, "saba-gomla")
            Action.RIYAL -> byCode(services, "saba-units")
        }
        "you" -> byCode(services, when (action) { Action.BALANCE, Action.RIYAL -> "you-balance"; Action.INSTANT -> "you-denomination"; Action.PACKAGES -> "you-offer"; Action.WHOLESALE -> "mtn-gomla" })
        "why" -> byCode(services, when (action) { Action.BALANCE, Action.RIYAL -> "why-balance"; Action.INSTANT, Action.WHOLESALE -> "why-bill"; Action.PACKAGES -> "why-package" })
        "yemen-4g" -> byCode(services, when (action) { Action.BALANCE -> if (purchase) "yem4g-balance" else "yem4g-query"; Action.INSTANT, Action.RIYAL -> "yem4g-balance"; Action.PACKAGES, Action.WHOLESALE -> "yem4g-package" })
        "yemen-net" -> byCode(services, when (action) { Action.BALANCE -> if (purchase) "post-adsl" else "post-query"; Action.INSTANT -> "post-line"; Action.PACKAGES, Action.WHOLESALE, Action.RIYAL -> "post-adsl" })
        "adenet" -> byCode(services, "adenet-bill", "adenet-query")
        else -> services.firstOrNull { it.serviceKind == if (purchase) "purchase" else "query" }
    }
}
private fun number(result: Map<String, Any?>?, keys: Set<String>): Double? {
    fun walk(v: Any?): Double? = when(v) {
        is Map<*,*> -> v.entries.firstNotNullOfOrNull { (k,x) -> val n=norm(k.toString()).replace(" ",""); if(keys.any(n::contains)) x?.toString()?.toDoubleOrNull() else walk(x) }
        is List<*> -> v.firstNotNullOfOrNull(::walk)
        else -> null
    }; return walk(result)
}
private fun text(result: Map<String, Any?>?, keys: Set<String>): String? {
    fun walk(v: Any?): String? = when(v) {
        is Map<*,*> -> v.entries.firstNotNullOfOrNull { (k,x) -> val n=norm(k.toString()).replace(" ",""); if(keys.any(n::contains) && x !is Map<*,*> && x !is List<*>) x?.toString() else walk(x) }
        is List<*> -> v.firstNotNullOfOrNull(::walk)
        else -> null
    }; return walk(result)
}
private fun fieldValue(field: ServiceFieldDto, selected: ServiceItemDto?, inputPhone: String, amount: String, method: String="Renew", solfa: String="N"): String? {
    val k = norm(field.key).replace(" ","")
    val l = norm(field.label)
    return when {
        k in setOf("mobile","phone","phonenumber","msisdn","mobilenumber","recipient","targetmobile") || l.contains("هاتف") || l.contains("جوال") -> phone(inputPhone)
        k in setOf("amount","value","price","num","rasid") || l.contains("المبلغ") -> amount.takeIf(String::isNotBlank)
        k in setOf("offerkey","offerid","offer","packageid","packagecode","itemid","code") -> selected?.metadata?.entries?.firstNotNullOfOrNull { (a,b) -> if(norm(a).replace(" ","") in setOf("offerkey","offerid","offer","packageid","packagecode","code","key")) b else null } ?: selected?.id?.toString()
        k == "method" -> method
        k == "solfa" -> solfa
        l.contains("نوع الخط") -> field.choices.firstOrNull()
        field.type.equals("select", true) -> field.choices.firstOrNull()
        else -> null
    }
}
private fun payload(service: ServiceDto, selected: ServiceItemDto?, inputPhone: String, amount: String): Map<String,String?> = service.fields.associate { it.key to fieldValue(it,selected,inputPhone,amount) }
private suspend fun submit(baseUrl:String, token:String, service:ServiceDto, inputPhone:String, amount:String, item:ServiceItemDto?):ServiceTransactionDto {
    val key=UUID.randomUUID().toString(); val p=payload(service,item,inputPhone,amount)
    val missing=service.fields.firstOrNull{it.required && p[it.key].isNullOrBlank() && item==null}; if(missing!=null) error("الحقل المطلوب: ${missing.label}")
    val api=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/")
    val r=api.submitServiceRequest("Token $token",key,ServiceRequestPayload(service.id,item?.type,item?.id,p,key)); if(!r.isSuccessful||r.body()==null) error("تعذر تنفيذ العملية (HTTP ${r.code()})")
    var tx=r.body()!!; repeat(30){ if(tx.status in setOf("success","failed","refunded","manual_review")||!tx.result.isNullOrEmpty()) return tx; kotlinx.coroutines.delay(850); api.getServiceTransaction("Token $token",tx.id).body()?.let{tx=it} }; return tx
}
private fun downloadTx(context: Context, tx:ServiceTransactionDto):Boolean { if(Build.VERSION.SDK_INT<Build.VERSION_CODES.Q)return false; return runCatching{val v=ContentValues().apply{put(MediaStore.Downloads.DISPLAY_NAME,"katolin-${tx.id.takeLast(12)}.txt");put(MediaStore.Downloads.MIME_TYPE,"text/plain");put(MediaStore.Downloads.RELATIVE_PATH,"Download/Katolin")};val u=context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,v)?:return false;context.contentResolver.openOutputStream(u)?.bufferedWriter()?.use{out->out.appendLine("كاتولين - إيصال العملية");out.appendLine("الحالة: ${tx.status}");out.appendLine("المرجع: ${tx.id}");tx.amount?.let{out.appendLine("المبلغ: $it ${tx.currency.orEmpty()}")};tx.providerTransactionId?.let{out.appendLine("معرف المزود: $it")};tx.result.orEmpty().forEach{(k,x)->out.appendLine("$k: $x")}}!=null}.getOrDefault(false)}
private fun syncLabel(ts:Long?):String=ts?.let{SimpleDateFormat("yyyy/MM/dd  HH:mm",Locale.US).format(Date(it))} ?: "لم تتم المزامنة بعد"

@Composable private fun Header(provider:Provider, syncing:Boolean, lastSync:Long?, onSync:()->Unit, onBack:()->Unit)=TopAppBar(
    title={Column(horizontalAlignment=Alignment.CenterHorizontally){Text("شبكة السداد",color=White,fontWeight=FontWeight.Black,fontSize=18.sp);Text("آخر مزامنة: ${syncLabel(lastSync)}",color=White.copy(.88f),fontSize=8.sp)}},
    navigationIcon={IconButton(onClick=onBack){Icon(Icons.Default.Wallet,null,tint=White)}},
    actions={IconButton(enabled=!syncing,onClick=onSync){if(syncing)CircularProgressIndicator(Modifier.size(20.dp),strokeWidth=2.dp,color=White) else Icon(Icons.Default.Refresh,null,tint=White)}},
    colors=TopAppBarDefaults.topAppBarColors(containerColor=provider.color)
)
@Composable private fun PhoneCard(provider:Provider, value:String)=Card(Modifier.fillMaxWidth(),RoundedCornerShape(18.dp),colors=CardDefaults.cardColors(White)){Row(Modifier.padding(12.dp),verticalAlignment=Alignment.CenterVertically){Surface(Modifier.size(54.dp),RoundedCornerShape(15.dp),provider.color.copy(.10f)){Box(contentAlignment=Alignment.Center){Text(provider.mark,color=provider.color,fontWeight=FontWeight.Black,fontSize=13.sp)}};Spacer(Modifier.width(10.dp));Column(Modifier.weight(1f),horizontalAlignment=Alignment.End){Text(provider.title,color=provider.color,fontWeight=FontWeight.Black,fontSize=18.sp);Text("البيانات تُستخدم من النسخة المحلية بعد المزامنة",color=Muted,fontSize=8.sp);Text(phone(value),color=TextDark,fontWeight=FontWeight.Bold,fontSize=11.sp)}}}
@Composable private fun PhoneField(value:String,onChange:(String)->Unit,provider:Provider)=OutlinedTextField(value,onChange,Modifier.fillMaxWidth(),singleLine=true,label={Text("رقم الهاتف")},leadingIcon={Icon(Icons.Default.Call,null,tint=provider.color)},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),shape=RoundedCornerShape(12.dp))
@Composable private fun Tabs(provider:Provider,action:Action,onPick:(Action)->Unit)=Surface(Modifier.fillMaxWidth(),RoundedCornerShape(14.dp),provider.color.copy(.09f)){Row(Modifier.fillMaxWidth().padding(3.dp)){listOf(Action.BALANCE to "رصيد",Action.INSTANT to "فوري",Action.PACKAGES to "باقات",Action.WHOLESALE to "جملة",Action.RIYAL to "ريال").forEach{(a,label)->Box(Modifier.weight(1f).clickable{onPick(a)},contentAlignment=Alignment.Center){Surface(RoundedCornerShape(10.dp),if(action==a)provider.color else Color.Transparent){Text(label,color=if(action==a)White else TextDark,fontWeight=FontWeight.Black,fontSize=10.sp,modifier=Modifier.padding(vertical=9.dp,horizontal=3.dp))}}}}}
@Composable private fun InfoCard(provider:Provider,balance:ServiceTransactionDto?,advance:ServiceTransactionDto?,lastSync:Long?)=Card(Modifier.fillMaxWidth(),RoundedCornerShape(17.dp),colors=CardDefaults.cardColors(White)){val b=number(balance?.result,setOf("balance","availablebalance","availablecredit","rasid"));val l=number(advance?.result,setOf("loan","sulfa","loanamount","sulfaamount","credit"));val t=text(balance?.result,setOf("mobiletype","linetype","mobiltype","type"));Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("بيانات الرقم",color=provider.color,fontWeight=FontWeight.Black,fontSize=14.sp);Text("محلي",color=Muted,fontSize=8.sp)};Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceEvenly){Mini("${money(b)}","رصيد الرقم",provider.color);Mini(t?:"—","نوع الخط",TextDark);Mini(if((l?:0.0)>0)money(l) else "لا توجد سلفة","فحص السلفة",if((l?:0.0)>0)Red else Green)};Text("آخر تحديث: ${syncLabel(lastSync)}",color=Muted,fontSize=8.sp,modifier=Modifier.fillMaxWidth(),textAlign=TextAlign.End)}}
@Composable private fun Mini(value:String,label:String,color:Color){Column(horizontalAlignment=Alignment.CenterHorizontally){Text(value,color=color,fontWeight=FontWeight.Black,fontSize=16.sp);Text(label,color=Muted,fontSize=8.sp)}}
@Composable private fun PackageCard(item:ServiceItemDto,provider:Provider,onClick:()->Unit){val m=item.metadata;val payment=m["payment_type"]?:m["paymentType"]?:"دفع مسبق";val line=m["line_type"]?:m["lineType"]?:"شريحة";val quota=m["quota"]?:m["data"];val days=m["validity_days"]?:m["days"]?:m["duration"];Card(Modifier.fillMaxWidth().clickable(onClick=onClick),RoundedCornerShape(17.dp),colors=CardDefaults.cardColors(White)){Column(Modifier.padding(11.dp),verticalArrangement=Arrangement.spacedBy(7.dp)){Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){Surface(RoundedCornerShape(13.dp),provider.color.copy(.10f),Modifier.size(50.dp)){Box(contentAlignment=Alignment.Center){Text(provider.mark,color=provider.color,fontWeight=FontWeight.Black)}};Spacer(Modifier.width(10.dp));Column(Modifier.weight(1f),horizontalAlignment=Alignment.End){Text(item.name,color=provider.color,fontWeight=FontWeight.Black,fontSize=14.sp);Text("$payment • $line",color=Muted,fontSize=8.sp,fontWeight=FontWeight.Bold)}};Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Column(horizontalAlignment=Alignment.End){Text("السعر",color=Muted,fontSize=8.sp);Text(item.price?:"—",color=TextDark,fontWeight=FontWeight.Black,fontSize=22.sp)};Column(horizontalAlignment=Alignment.End){quota?.let{Text("الحجم: $it",color=Muted,fontSize=8.sp)};days?.let{Text("المدة: $it",color=Muted,fontSize=8.sp)}}};Button(onClick=onClick,Modifier.fillMaxWidth().height(42.dp),colors=ButtonDefaults.buttonColors(containerColor=provider.color),shape=RoundedCornerShape(11.dp)){Text("تسديد وتفعيل",fontWeight=FontWeight.Black,fontSize=11.sp)}}}}
@Composable private fun PackageTree(provider:Provider,service:ServiceDto?,onPick:(ServiceItemDto)->Unit){val items=service?.items.orEmpty().filter{it.type.contains("plan",true)||it.type.contains("offer",true)||it.type.contains("telecom",true)};val by=service?.planTypes.orEmpty();var expanded by remember(items){mutableStateOf(by.firstOrNull()?.id)};Column(verticalArrangement=Arrangement.spacedBy(7.dp)){if(by.isNotEmpty())by.forEach{type->val set=type.planIds.mapNotNull{id->items.firstOrNull{it.id==id}};if(set.isNotEmpty()){Card(Modifier.fillMaxWidth().clickable{expanded=if(expanded==type.id)null else type.id},RoundedCornerShape(12.dp),colors=CardDefaults.cardColors(provider.color.copy(.08f))){Row(Modifier.fillMaxWidth().padding(11.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(if(expanded==type.id)"⌃" else "⌄",color=provider.color);Text(type.name,color=provider.color,fontWeight=FontWeight.Black,fontSize=12.sp)}};if(expanded==type.id)set.forEach{PackageCard(it,provider){onPick(it)}}}}else items.forEach{PackageCard(it,provider){onPick(it)}};if(items.isEmpty())Text("لا توجد باقات محفوظة. نفّذ المزامنة أولًا.",color=Muted,modifier=Modifier.fillMaxWidth().padding(16.dp),textAlign=TextAlign.Center)}}

@Composable fun PaymentNetworkScreen(wallet:WalletAccount,packages:List<TelecomPackage>,formatMoney:(Double)->String,onBackClick:()->Unit,onSyncBalance:()->Unit,onRechargeSubmit:(String,String,String,String,Double)->Unit,modifier:Modifier=Modifier){
    val repo=remember{StoreRepository.instance};val baseUrl by repo.djangoBaseUrl.collectAsState();val session by repo.userSession.collectAsState();val scope=rememberCoroutineScope();var phoneValue by remember(session.phone){mutableStateOf(session.phone)};val p=provider(phoneValue);val context=LocalContext.current
    var state by remember{mutableStateOf(PaymentSnapshotCache.loadCatalog()?.let{CachedState(catalog=it,settings=PaymentSnapshotCache.loadSettings(),lastSync=PaymentSnapshotCache.loadLastSync())}?:CachedState())};var action by remember{mutableStateOf(Action.BALANCE)};var syncing by remember{mutableStateOf(false)};var amount by remember{mutableStateOf("")};var selectedItem by remember{mutableStateOf<ServiceItemDto?>(null)};var selectedService by remember{mutableStateOf<ServiceDto?>(null)};var operation by remember{mutableStateOf<ServiceTransactionDto?>(null)};var duplicateCount by remember{mutableStateOf(0)};var showDuplicate by remember{mutableStateOf(false)};var showConfirm by remember{mutableStateOf(false)};var error by remember{mutableStateOf<String?>(null)};var downloaded by remember{mutableStateOf(false)}
    val services=remember(state.catalog){flatten(state.catalog?.categories.orEmpty())}
    fun loadPhone(){val x=PaymentSnapshotCache.loadPhoneSnapshot(phoneValue);state=state.copy(balance=x.first,advance=x.second,offers=x.third,reports=PaymentSnapshotCache.loadReports(phoneValue))}
    LaunchedEffect(Unit){loadPhone()}
    LaunchedEffect(phoneValue){loadPhone()}
    fun sync(){val token=session.token;if(token==null){error="سجل الدخول أولًا.";return};if(phone(phoneValue).isBlank()){error="أدخل رقم الهاتف أولًا.";return};scope.launch{syncing=true;error=null;runCatching{val api=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/");val cat=api.getServiceCatalog("Token $token").body() ?: throw IllegalStateException("تعذر تحميل الكتالوج");val st=api.getServiceSettings("Token $token",configured="1").body() ?: ServiceSettingsResponse();val all=flatten(cat.categories);val bal=resolve(st.settings,all,p,Action.BALANCE,false);val adv=settingService(st.settings,all,p,"advance","loan","سلفة") ?: byCode(all,"yem-advance-query","yem-query-advance");val offers=resolve(st.settings,all,p,Action.PACKAGES,false);val jobs=listOfNotNull(bal,adv,offers).distinctBy{it.id}.map{srv->async{submit(baseUrl,token,srv,phoneValue,"",null)}}.awaitAll();val b=jobs.firstOrNull{it.service==bal?.code};val a=jobs.firstOrNull{it.service==adv?.code};val o=jobs.firstOrNull{it.service==offers?.code};val reportService=resolve(st.settings,all,p,Action.BALANCE,true)?:offers;val reports=reportService?.let{api.getServiceReports("Token $token",mobile=phone(phoneValue),today="1",service=it.code).body()};PaymentSnapshotCache.saveCatalog(cat);PaymentSnapshotCache.saveSettings(st);PaymentSnapshotCache.savePhoneSnapshot(phoneValue,b,a,o);reports?.let{PaymentSnapshotCache.saveReports(phoneValue,it)};PaymentSnapshotCache.saveLastSync();state=CachedState(cat,st,b,a,o,reports,PaymentSnapshotCache.loadLastSync())}.onFailure{error=it.localizedMessage?:"فشلت المزامنة"};syncing=false}}
    fun choose(item:ServiceItemDto?,service:ServiceDto?){if(service==null){error="الخدمة غير مهيأة في الإعدادات الأساسية.";return};selectedItem=item;selectedService=service;duplicateCount=state.reports?.results.orEmpty().size;if(duplicateCount>0)showDuplicate=true else showConfirm=true}
    fun purchase(){val token=session.token?:return;val service=selectedService?:return;scope.launch{error=null;runCatching{operation=submit(baseUrl,token,service,phoneValue,amount,selectedItem);operation?.let{PaymentSnapshotCache.saveOperation(phoneValue,it)};showConfirm=false;showDuplicate=false;downloaded=false;if(operation?.status=="success"){onSyncBalance();onRechargeSubmit(phoneValue,p.title,service.name,selectedItem?.name?:service.name,operation?.amount?.toDoubleOrNull()?:selectedItem?.price?.toDoubleOrNull()?:amount.toDoubleOrNull()?:0.0)}}.onFailure{error=it.localizedMessage?:"تعذر تنفيذ التسديد"}}}
    Scaffold(modifier.fillMaxSize(),topBar={Header(p,syncing,state.lastSync,::sync,onBackClick)}){pad->LazyColumn(Modifier.fillMaxSize().padding(pad).background(Bg),contentPadding=PaddingValues(10.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){item{PhoneCard(p,phoneValue)};item{PhoneField(phoneValue,{phoneValue=it},p)};item{Tabs(p,action){action=it}};item{InfoCard(p,state.balance,state.advance,state.lastSync)}
        when(action){
            Action.BALANCE->{item{val service=resolve(state.settings?.settings.orEmpty(),services,p,Action.BALANCE,true);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(7.dp)){Button(onClick={choose(null,service)},Modifier.weight(1f).height(44.dp),colors=ButtonDefaults.buttonColors(containerColor=p.color),shape=RoundedCornerShape(11.dp)){Text("تسديد الرصيد",fontWeight=FontWeight.Black,fontSize=10.sp)};Surface(RoundedCornerShape(11.dp),p.color.copy(.09f),Modifier.weight(1f)){Text("الاستعلام محفوظ حتى المزامنة",color=p.color,fontWeight=FontWeight.Black,fontSize=9.sp,modifier=Modifier.padding(13.dp),textAlign=TextAlign.Center)}}}}
            Action.INSTANT->{item{val service=resolve(state.settings?.settings.orEmpty(),services,p,Action.INSTANT,true);Column(verticalArrangement=Arrangement.spacedBy(7.dp)){service?.items.orEmpty().filter{it.type.contains("denomination",true)||it.type.contains("recharge",true)||it.type.contains("card",true)}.take(60).forEach{item{PackageCard(it,p){choose(it,service)}}};if(service?.items.orEmpty().isEmpty())Text("لا توجد فئات محفوظة. نفّذ المزامنة.",color=Muted,modifier=Modifier.fillMaxWidth().padding(16.dp),textAlign=TextAlign.Center)}}}
            Action.PACKAGES->{item{val service=resolve(state.settings?.settings.orEmpty(),services,p,Action.PACKAGES,true);Text("الباقات المتاحة من آخر مزامنة",color=TextDark,fontWeight=FontWeight.Black,fontSize=14.sp,modifier=Modifier.fillMaxWidth(),textAlign=TextAlign.End);PackageTree(p,service){choose(it,service)};val active=(state.offers?.result?.get("offers") as? List<*>)?.mapNotNull{row->(row as? Map<*,*>)?.entries?.firstNotNullOfOrNull{(k,v)->if(norm(k.toString()).replace(" ","") in setOf("offername","name","description"))v?.toString() else null}}.orEmpty();if(active.isNotEmpty()){Text("الباقات الحالية للرقم",color=p.color,fontWeight=FontWeight.Black,fontSize=12.sp,modifier=Modifier.fillMaxWidth().padding(top=4.dp),textAlign=TextAlign.End);active.take(8).forEach{Surface(RoundedCornerShape(11.dp),Green.copy(.08f)){Text(it,color=Green,fontWeight=FontWeight.Bold,fontSize=9.sp,modifier=Modifier.fillMaxWidth().padding(9.dp),textAlign=TextAlign.End)}}}}}
            Action.WHOLESALE,Action.RIYAL->{item{val service=resolve(state.settings?.settings.orEmpty(),services,p,action,true);OutlinedTextField(amount,{amount=it},Modifier.fillMaxWidth(),singleLine=true,label={Text("المبلغ")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number),shape=RoundedCornerShape(12.dp));Button(onClick={choose(null,service)},Modifier.fillMaxWidth().height(46.dp),colors=ButtonDefaults.buttonColors(containerColor=p.color),shape=RoundedCornerShape(11.dp)){Text("متابعة التسديد",fontWeight=FontWeight.Black)}}}
        }
        error?.let{msg->item{Text(msg,color=Red,fontWeight=FontWeight.Bold,fontSize=10.sp,modifier=Modifier.fillMaxWidth().padding(8.dp),textAlign=TextAlign.Center)}}
        item{Text("المزامنة الوحيدة من الخادم هي عبر 🔄 أعلى الشاشة. فتح الشاشة والتنقل بين التبويبات لا يرسل أي طلب.",color=Muted,fontSize=8.sp,modifier=Modifier.fillMaxWidth().padding(top=3.dp),textAlign=TextAlign.Center)}}}
    if(showDuplicate)AlertDialog(onDismissRequest={showDuplicate=false},title={Text("تنبيه قبل التسديد",color=p.color,fontWeight=FontWeight.Black)},text={Text("يوجد $duplicateCount تسديد/عمليات محفوظة لنفس الرقم اليوم وفق آخر مزامنة. هل تريد تنفيذ تسديد آخر؟",fontSize=12.sp)},confirmButton={Button(onClick={showDuplicate=false;showConfirm=true},colors=ButtonDefaults.buttonColors(containerColor=p.color)){Text("نعم، تسديد مرة أخرى")}},dismissButton={TextButton(onClick={showDuplicate=false}){Text("إلغاء")}})
    if(showConfirm)AlertDialog(onDismissRequest={showConfirm=false},title={Text("تأكيد العملية",fontWeight=FontWeight.Black)},text={Column(verticalArrangement=Arrangement.spacedBy(6.dp)){Text(selectedItem?.name?:selectedService?.name.orEmpty(),color=p.color,fontWeight=FontWeight.Black,fontSize=14.sp);Text("الرقم: ${phone(phoneValue)}");Text("المبلغ: ${selectedItem?.price?:amount.ifBlank{"—"}} ر.ي");Text("سيتم إرسال طلب التنفيذ فقط بعد تأكيدك.",color=Muted,fontSize=9.sp)}},confirmButton={Button(onClick=::purchase,colors=ButtonDefaults.buttonColors(containerColor=p.color)){Text("تأكيد التسديد")}},dismissButton={TextButton(onClick={showConfirm=false}){Text("إلغاء")}})
    operation?.let{tx->AlertDialog(onDismissRequest={operation=null},title={Row(verticalAlignment=Alignment.CenterVertically){Icon(Icons.Default.CheckCircle,null,tint=if(tx.status=="success")Green else Red,modifier=Modifier.size(24.dp));Spacer(Modifier.width(7.dp));Text("نتيجة العملية",fontWeight=FontWeight.Black)}},text={Column(verticalArrangement=Arrangement.spacedBy(6.dp)){Text(if(tx.status=="success")"تمت العملية بنجاح" else tx.errorMessage?:"تعذر تنفيذ العملية",color=if(tx.status=="success")Green else Red,fontWeight=FontWeight.Black);Text("المرجع: ${tx.id}",fontSize=9.sp);tx.providerTransactionId?.let{Text("معرف المزود: $it",fontSize=9.sp)}},},confirmButton={Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){Button(onClick={downloaded=downloadTx(context,tx)},colors=ButtonDefaults.buttonColors(containerColor=p.color)){Text(if(downloaded)"تم التحميل ✓" else "تحميل")};TextButton(onClick={operation=null}){Text("إغلاق")}}})}
}
