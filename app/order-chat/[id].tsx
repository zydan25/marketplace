import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";

type Message = { id: number; body: string; sender: { id: number; role: string; first_name: string }; created_at: string };
type Conversation = { id: number; subject: string; messages: Message[] };

export default function OrderChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, isAuthenticated } = useAuth();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const data = await ApiClient.get<{ results: Conversation[] }>(`/api/conversations/?order=${id}`);
      if (data.results && data.results.length > 0) {
        setConversation(data.results[0]);
      } else {
        // Create conversation if it doesn't exist
        const newConv = await ApiClient.post<Conversation>("/api/conversations/", { order: id, subject: `طلب #${id}` });
        setConversation(newConv);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (isAuthenticated && id) load(); }, [id, isAuthenticated]);

  async function send() {
    if (!conversation || !draft.trim()) return;
    try {
      setSending(true);
      await ApiClient.post(`/api/conversations/${conversation.id}/send_message/`, { body: draft });
      setDraft("");
      await load();
    } catch (error) {
      Alert.alert("خطأ", "تعذر إرسال الرسالة");
    } finally {
      setSending(false);
    }
  }

  if (!isAuthenticated) return <ScreenContainer><View style={styles.center}><Text>سجل الدخول أولاً</Text></View></ScreenContainer>;
  if (loading && !conversation) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023" /></View></ScreenContainer>;

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity>
        <Text style={styles.headerTitle}>محادثة الطلب</Text>
        <View style={{ width: 25 }} />
      </View>

      <FlatList
        data={conversation?.messages || []}
        keyExtractor={item => String(item.id)}
        contentContainerStyle={styles.list}
        inverted
        renderItem={({ item }) => {
          const own = item.sender.id === user?.id;
          return (
            <View style={[styles.bubbleWrapper, own ? styles.ownWrapper : styles.otherWrapper]}>
              <View style={[styles.bubble, own ? styles.ownBubble : styles.otherBubble]}>
                <Text style={[styles.msgText, own && styles.ownText]}>{item.body}</Text>
                <Text style={[styles.time, own && styles.ownTime]}>{new Date(item.created_at).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" })}</Text>
              </View>
            </View>
          );
        }}
      />

      <View style={styles.composer}>
        <TextInput value={draft} onChangeText={setDraft} style={styles.input} placeholder="اكتب رسالتك هنا..." textAlign="right" onSubmitEditing={send} />
        <TouchableOpacity style={styles.sendBtn} onPress={send} disabled={sending}>
          <MaterialIcons name="send" size={20} color="#FFF" />
        </TouchableOpacity>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#EEE" },
  headerTitle: { fontSize: 16, fontWeight: "900" },
  list: { padding: 14, gap: 10 },
  bubbleWrapper: { width: "100%", flexDirection: "row", marginBottom: 10 },
  ownWrapper: { justifyContent: "flex-start" },
  otherWrapper: { justifyContent: "flex-end" },
  bubble: { maxWidth: "80%", padding: 12, borderRadius: 12 },
  ownBubble: { backgroundColor: "#111", borderBottomLeftRadius: 0 },
  otherBubble: { backgroundColor: "#FFF", borderBottomRightRadius: 0 },
  msgText: { fontSize: 14, color: "#111", textAlign: "right" },
  ownText: { color: "#FFF" },
  time: { fontSize: 10, color: "#888", marginTop: 4, textAlign: "right" },
  ownTime: { color: "#CCC" },
  composer: { flexDirection: "row-reverse", padding: 10, backgroundColor: "#FFF", borderTopWidth: 1, borderColor: "#EEE", alignItems: "center", gap: 10 },
  input: { flex: 1, backgroundColor: "#F5F5F5", borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 14 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" }
});
