@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.SessionStore
import com.example.data.model.TelecomPackage
import com.example.data.model.WalletAccount
import com.example.data.remote.*
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private val Bg = Color(0xFFF6F4F8)
private val Pink = Color(0xFFC01855)

private fun digits(v: String): String = v.map { c ->
    when (c) {
        '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4'; '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9'
        '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4'; '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9'
        else -> c
    }
}.joinToString("")

private fun isYm(phone: String) = digits(phone).filter(Char::isDigit).let { it.startsWith("77") || it.startsWith("78") }

private fun accent(p: ServiceCategoryDto?) = when {
    p == null -> Color(0xFF39445A)
    "yemen-mobile" in "${p.slug} ${p.name}".lowercase() || "يمن موبايل" in p.name -> Pink
    "sabafon" in "${p.slug} ${p.name}".lowercase() || "سبأفون" in p.name -> Color(0xFF1976B8)
    "you" in "${p.slug} ${p.name}".lowercase() || "يو" in p.name -> Color(0xFFD08A00)
    "why" in "${p.slug} ${p.name}".lowercase() || "واي" in p.name -> Color(0xFF6C4390)
    "4g" in "${p.slug} ${p.name}".lowercase() || "فورجي" in p.name -> Color(0xFF0A8787)
    "yemen-net" in "${p.slug} ${p.name}".lowercase() || "يمن نت" in p.name -> Color(0xFF2D5B99)
    else -> Color(0xFF39445A)
}

private fun title(p: ServiceCategoryDto?) = when {
    p == null -> "شبكة السداد"
    "yemen-mobile" in "${p.slug} ${p.name}".lowercase() || "يمن موبايل" in p.name -> "Yemen Mobile"
    else -> p.name
}

private fun flatten(c: ServiceCategoryDto): List<ServiceDto> = c.services + c.children.flatMap(::flatten)
private fun findQuery(s: List<ServiceDto>, offers: Boolean) = s.firstOrNull {
    if (it.serviceKind != "query") return@firstOrNull false
    val x = "${it.code} ${it.name}".lowercase()
    val isOffer = "offer" in x || "باقة" in x || "باقات" in x || "عروض" in x
    isOffer == offers
}
private fun findPurchase(s: List<ServiceDto>, offers: Boolean) = s.firstOrNull {
    if (it.serviceKind != "purchase") return@firstOrNull false
    val x = "${it.code} ${it.name}".lowercase()
    val isOffer = "offer" in x || "باقة" in x || "باقات" in x
    isOffer == offers
}
private fun showValue(v: Any?): String = when(v) { null -> "—"; is Map<*,*> -> v.entries.joinToString("\n") { "${it.key}: ${showValue(it.value)}" }; is List<*> -> v.joinToString("\n") { showValue(it) }; else -> v.toString() }

@Composable
private fun ResultDialog(tx: ServiceTransactionDto, close: () -> Unit) {
    AlertDialog(onDismissRequest = close, title = { Text("نتيجة العملية", fontWeight = FontWeight.Black) }, text = {
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            item { Text(when(tx.status) { "success" -> "تمت العملية بنجاح ✅"; "pending_provider", "processing", "queued", "accepted" -> "العملية لدى المزود ⏳"; "refunded" -> "أعيد المبلغ للمحفظة"; "manual_review" -> "تحتاج العملية مراجعة"; else -> tx.errorMessage ?: "تعذر تنفيذ العملية" }, fontWeight = FontWeight.Bold) }
            item { Text("المرجع: ${tx.id}", color = Color.Gray, fontSize = 10.sp) }
            tx.amount?.let { item { Text("المبلغ: $it ${tx.currency.orEmpty()}") } }
            tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Color.Gray, fontSize = 10.sp) } }
            tx.result.orEmpty().forEach { (k,v) -> item { Column { Text(k, color = Color.Gray, fontSize = 9.sp); Text(showValue(v), fontWeight = FontWeight.Bold, fontSize = 11.sp) } } }
        }
    }, confirmButton = { TextButton(onClick = close) { Text("إغلاق") } })
}

@Composable
fun PaymentNetworkScreen(
    wallet: WalletAccount,
    packages: List<TelecomPackage>,
    formatMoney: (Double) -> String,
    onBackClick: () -> Unit,
    onSyncBalance: () -> Unit,
    onRechargeSubmit: (phone: String, operatorName: String, category: String, packageName: String, amount: Double) -> Unit,
    modifier: Modifier = Modifier
) {
    val repo = remember { StoreRepository.instance }
    val baseUrl by repo.djangoBaseUrl.collectAsState()
    val session by repo.userSession.collectAsState()
    val scope = rememberCoroutineScope()
    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var provider by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var service by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var selectedOffer by remember { mutableStateOf<Map.Entry<String,Any?>?>(null) }
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    var amount by remember { mutableStateOf("") }
    var syncing by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var showResult by remember { mutableStateOf(false) }
    var showReports by remember { mutableStateOf(false) }
    val values = remember { mutableStateMapOf<String,String>() }
    val key = "service_catalog_${baseUrl.trimEnd('/') }"

    fun restore() { SessionStore.loadLocalString(key)?.let { raw -> runCatching { NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).fromJson(raw) }.getOrNull()?.let { catalog = it.categories } } }
    fun syncCatalog() { if (syncing) return; scope.launch { syncing=true; error=null; try { val token=session.token ?: error("سجل الدخول أولًا"); val r=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/").getServiceCatalog("Token $token"); if(!r.isSuccessful||r.body()==null) error("تعذر تحميل الكتالوج (HTTP ${r.code()})"); else { catalog=r.body()!!.categories; SessionStore.saveLocalString(key, NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).toJson(r.body()!!)); provider=null; service=null } } catch(e:Exception){ error=e.localizedMessage ?: "تعذر المزامنة" } finally { syncing=false } } }
    LaunchedEffect(baseUrl,session.token) { restore() }

    val root = catalog.firstOrNull { it.slug=="payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = root?.categories.orEmpty()
    val services = provider?.let(::flatten).orEmpty().distinctBy { it.id }
    val a = accent(provider)
    val ym = isYm(phone)

    fun chooseProvider(p:ServiceCategoryDto){ provider=p; service=null; selectedItem=null; selectedOffer=null; result=null; values.clear() }
    fun chooseService(s:ServiceDto){ service=s; selectedItem=null; result=null; amount=""; values.clear(); s.fields.forEach { if(it.key=="mobile") values[it.key]=digits(phone); if(it.type=="select"&&it.choices.isNotEmpty()) values[it.key]=it.choices.first() } }
    fun queryOffers() { val s=findQuery(services,true) ?: run{error="لا يوجد استعلام باقات مهيأ لهذا المزود";return}; chooseService(s); runQuery(s) }
    fun queryBalance() { val s=findQuery(services,false) ?: run{error="لا يوجد استعلام رصيد مهيأ لهذا المزود";return}; chooseService(s); runQuery(s) }
    fun runQuery(s:ServiceDto){ val token=session.token ?: return; scope.launch { busy=true; error=null; try { val id=UUID.randomUUID().toString(); val body=ServiceRequestPayload(s.id,null,null,values.toMap(),id); val r=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/").submitServiceRequest("Token $token",id,body); if(!r.isSuccessful||r.body()==null) error="تعذر الاستعلام (HTTP ${r.code()})" else { result=r.body(); showResult=true } } catch(e:Exception){error=e.localizedMessage?:"فشل الاستعلام"} finally{busy=false} } }
    fun purchase(){ val s=service?:return; val token=session.token?:return; scope.launch{busy=true;error=null;try{val p=values.toMutableMap(); selectedItem?.metadata?.get("offerid")?.let{p["offerid"]=it}; selectedItem?.metadata?.get("offerkey")?.let{p["offerkey"]=it}; selectedOffer?.let{p["offerid"]=it.value?.toString().orEmpty()}; if(amount.isNotBlank()) p["amount"]=amount; val missing=s.fields.firstOrNull{it.required&&p[it.key].isNullOrBlank()}; if(missing!=null) throw IllegalStateException("الحقل المطلوب: ${missing.label}"); val id=UUID.randomUUID().toString(); val body=ServiceRequestPayload(s.id,selectedItem?.type,selectedItem?.id,p.mapValues{it.value},id); val r=NetworkClient.getApiService(baseUrl.trimEnd('/')+"/").submitServiceRequest("Token $token",id,body); if(!r.isSuccessful||r.body()==null) throw IllegalStateException("تعذر التسديد (HTTP ${r.code()})"); result=r.body();showResult=true; if(result?.status=="success"||result?.status=="refunded")onSyncBalance(); if(result?.status=="success")onRechargeSubmit(phone,title(provider),s.name,selectedItem?.name?:selectedOffer?.key?:s.name,result?.amount?.toDoubleOrNull()?:0.0)}catch(e:Exception){error=e.localizedMessage?:"حدث خطأ"}finally{busy=false}}}

    if(showReports){ ServiceReportsScreen(onBackClick={showReports=false},modifier=modifier); return }
    Scaffold(modifier.fillMaxSize(), topBar={TopAppBar(title={Text("شبكة السداد",fontWeight=FontWeight.Black)},navigationIcon={IconButton(onClick=onBackClick){Icon(Icons.AutoMirrored.Filled.ArrowBack,"رجوع")}},actions={IconButton(onClick={showReports=true}){Icon(Icons.Default.Inventory2,"التقرير")};IconButton(onClick={::syncCatalog}){Icon(Icons.Default.CloudDownload,"مزامنة")}},colors=TopAppBarDefaults.topAppBarColors(containerColor=if(ym)Pink.copy(alpha=.08f) else Bg))}){pad->
        LazyColumn(Modifier.fillMaxSize().padding(pad).background(Bg),contentPadding=PaddingValues(12.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){
            item{Card(shape=RoundedCornerShape(24.dp),colors=CardDefaults.cardColors(if(ym)Pink.copy(alpha=.10f) else Color.White)){Column(Modifier.padding(15.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text("خدمات التسديد",fontSize=21.sp,fontWeight=FontWeight.Black);Text(if(catalog.isEmpty())"اضغط مزامنة لتحميل الباقات والخدمات وحفظها." else "البيانات محفوظة على الجهاز — لا مزامنة تلقائية.",color=Color.Gray,fontSize=10.sp)}Surface(shape=CircleShape,color=if(ym)Pink else a.copy(alpha=.12f),modifier=Modifier.size(58.dp)){Box(contentAlignment=Alignment.Center){Text(if(ym)"YM" else "K",color=if(ym)Color.White else a,fontWeight=FontWeight.Black)}}};OutlinedTextField(phone,{phone=it;service?.let{values["mobile"]=digits(phone)}},Modifier.fillMaxWidth(),singleLine=true,label={Text("رقم الهاتف / المستفيد")},leadingIcon={Icon(Icons.Default.Call,null,tint=if(ym)Pink else a)},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),shape=RoundedCornerShape(15.dp));if(ym)Text("Yemen Mobile • تم التعرف على الرقم 77/78",color=Pink,fontWeight=FontWeight.Bold,fontSize=10.sp)}}}
            item{Card(shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(Color.White)){Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("الشركات",fontWeight=FontWeight.ExtraBold);Text("من الكتالوج المحفوظ",color=Color.Gray,fontSize=9.sp)};Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)){providers.forEach{p->val sel=provider?.id==p.id;Surface(Modifier.width(120.dp).clickable{chooseProvider(p)},RoundedCornerShape(16.dp),if(sel)accent(p)else Color(0xFFFAF9FB)){Column(Modifier.padding(10.dp),horizontalAlignment=Alignment.CenterHorizontally){Text(title(p).take(3),fontWeight=FontWeight.Black,color=if(sel)Color.White else accent(p));Text(title(p),fontSize=10.sp,fontWeight=FontWeight.Bold,color=if(sel)Color.White else Color.Black)}}}}}}}
            if(provider!=null)item{Card(shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(Color.White)){Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){Text(title(provider),fontWeight=FontWeight.Black,fontSize=18.sp,color=a);Row(horizontalArrangement=Arrangement.spacedBy(7.dp)){FilterChip(false,{queryBalance()},label={Text("الرصيد")},leadingIcon={Icon(Icons.Default.AccountBalanceWallet,null,Modifier.size(16.dp))});FilterChip(false,{queryOffers()},label={Text("الباقات")},leadingIcon={Icon(Icons.Default.Inventory2,null,Modifier.size(16.dp))});FilterChip(false,{findPurchase(services,false)?.let(::chooseService)?:run{error="لا توجد خدمة تسديد"}},label={Text("تسديد")})}}}
            service?.let{s->item{Card(shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(Color.White)){Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){Text(s.name,fontWeight=FontWeight.Black,fontSize=18.sp,color=a);s.items.take(40).forEach{it->Surface(Modifier.fillMaxWidth().clickable{selectedItem=it},RoundedCornerShape(13.dp),Color(0xFFFAF9FB),border=androidx.compose.foundation.BorderStroke(1.dp,if(selectedItem?.id==it.id)a else Color(0xFFE8E5EA))){Row(Modifier.padding(10.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(it.name,fontWeight=FontWeight.Bold,fontSize=11.sp);Text(it.price?:"—",color=a,fontWeight=FontWeight.Black,fontSize=10.sp)}}};s.fields.filter{it.key!="mobile"&&it.key!in setOf("external_code","num","packageid","uniqcode")}.forEach{f->OutlinedTextField(values[f.key].orEmpty(),{values[f.key]=it},Modifier.fillMaxWidth(),singleLine=true,label={Text(f.label+if(f.required)" *"else"")},shape=RoundedCornerShape(13.dp))};if(s.pricingMode=="amount"||s.name.contains("رصيد")||s.name.contains("شحن"))OutlinedTextField(amount,{amount=it},Modifier.fillMaxWidth(),singleLine=true,label={Text("المبلغ")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number),shape=RoundedCornerShape(13.dp));Button(onClick={if(s.serviceKind=="query")runQuery(s)else purchase()},enabled=!busy,Modifier.fillMaxWidth().height(49.dp),shape=RoundedCornerShape(14.dp),colors=ButtonDefaults.buttonColors(containerColor=a)){if(busy)CircularProgressIndicator(Modifier.size(17.dp),color=Color.White,strokeWidth=2.dp)else Icon(if(s.serviceKind=="query")Icons.Default.Search else Icons.Default.CheckCircle,null,Modifier.size(18.dp));Spacer(Modifier.width(7.dp));Text(if(s.serviceKind=="query")"استعلام"else"تسديد + تفعيل",fontWeight=FontWeight.Black)}}}}}
            error?.let{m->item{Text(m,color=Color(0xFFC23A3A),modifier=Modifier.fillMaxWidth().background(Color(0xFFFFEEEE),RoundedCornerShape(14.dp)).padding(12.dp),textAlign=TextAlign.Center,fontSize=10.sp)}}
            if(syncing)item{Box(Modifier.fillMaxWidth().padding(25.dp),contentAlignment=Alignment.Center){CircularProgressIndicator(color=a)}}
        }
    }
    if(showResult&&result!=null)ResultDialog(result!!){showResult=false}
}