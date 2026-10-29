import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator, Animated, KeyboardAvoidingView, Platform, Pressable,
  RefreshControl, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as DocumentPicker from 'expo-document-picker';
import {
  AnswerResult, askDocument, beginLogin, clearToken, DocumentItem,
  getMe, listDocuments, logout, readToken, saveToken, uploadDocument, verifyLogin,
} from './src/api';

const C = { bg: '#07111f', panel: '#101d2e', text: '#eff6ff', muted: '#9aadc5', teal: '#63e6cf', blue: '#7aa8ff', danger: '#ff9b9b', line: 'rgba(181,205,235,.13)' };
type Tab = 'library' | 'ask';

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [otpPending, setOtpPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>('library');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<AnswerResult | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const entrance = useRef(new Animated.Value(0)).current;
  const documentsRef = useRef<DocumentItem[]>([]);
  documentsRef.current = documents;
  const selected = useMemo(() => documents.find((d) => d.id === selectedId) || null, [documents, selectedId]);

  const refresh = useCallback(async (key: string, showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    try {
      const items = await listDocuments(key);
      setDocuments(items);
      setSelectedId((current) => current && items.some((d) => d.id === current)
        ? current : (items.find((d) => d.status === 'ready') || items[0])?.id ?? null);
      setError('');
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Unable to load documents.';
      const status = (cause as Error & { status?: number }).status;
      if (status === 401 || status === 403) { await clearToken(); setToken(null); }
      setError(message);
    } finally { setRefreshing(false); }
  }, []);

  useEffect(() => {
    readToken().then(setToken).catch(() => setToken(null));
    Animated.spring(entrance, { toValue: 1, useNativeDriver: true, damping: 18, stiffness: 95 }).start();
  }, [entrance]);

  useEffect(() => {
    if (!token) return;
    refresh(token);
    getMe(token).then((profile) => setUsername(profile.username)).catch(() => {});
    const timer = setInterval(() => {
      if (documentsRef.current.some((d) => d.status === 'processing')) refresh(token);
    }, 7000);
    return () => clearInterval(timer);
  }, [token, refresh]);

  async function startLogin() {
    setBusy(true); setError('');
    try {
      const result = await beginLogin(username.trim(), password);
      setUsername(result.username); setPassword(''); setOtpPending(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not sign in.'); }
    finally { setBusy(false); }
  }

  async function finishLogin() {
    setBusy(true); setError('');
    try {
      const result = await verifyLogin(username, otp.trim());
      await saveToken(result.token); setOtp(''); setOtpPending(false); setToken(result.token);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not verify that code.'); }
    finally { setBusy(false); }
  }

  async function upload() {
    setError('');
    const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'text/plain'], copyToCacheDirectory: true });
    if (result.canceled || !token) return;
    const asset = result.assets[0];
    if ((asset.size ?? 0) > 25 * 1024 * 1024) { setError('Choose a file smaller than 25 MB.'); return; }
    setBusy(true);
    try { await uploadDocument(token, asset); await refresh(token); setTab('library'); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Upload failed.'); }
    finally { setBusy(false); }
  }

  async function ask() {
    if (!token || !selected || !question.trim()) return;
    setBusy(true); setError(''); setAnswer(null);
    try { setAnswer(await askDocument(token, selected.id, question.trim())); setQuestion(''); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not generate an answer.'); }
    finally { setBusy(false); }
  }

  async function signOut() {
    if (token) { try { await logout(token); } catch { await clearToken(); } }
    setToken(null); setDocuments([]); setAnswer(null); setOtpPending(false); setError('');
  }

  const enterStyle = { opacity: entrance, transform: [{ translateY: entrance.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }] };
  if (!token) return (
    <LinearGradient colors={['#07111f', '#0b1d31', '#102e43']} style={s.page}>
      <StatusBar barStyle="light-content" /><View style={s.glow} />
      <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={s.loginScroll} keyboardShouldPersistTaps="handled">
          <Animated.View style={[s.loginCard, enterStyle]}>
            <View style={s.brand}><Text style={s.brandText}>D</Text></View>
            <Text style={s.eyebrow}>YOUR DOCUMENTS, IN DIALOGUE</Text>
            <Text style={s.loginTitle}>Knowledge,{'\n'}within reach.</Text>
            <Text style={s.loginCopy}>Sign in to your private library and ask better questions of every document.</Text>
            <View style={s.form}>
              {!otpPending ? <>
                <Field label="USERNAME" value={username} onChangeText={setUsername} autoCapitalize="none" placeholder="Your username" />
                <Field label="PASSWORD" value={password} onChangeText={setPassword} secureTextEntry placeholder="Your password" />
                <Button title="Continue" onPress={startLogin} loading={busy} />
              </> : <>
                <Text style={s.otpNote}>A six-digit code is on its way to the email attached to @{username}.</Text>
                <Field label="EMAIL CODE" value={otp} onChangeText={(v) => setOtp(v.replace(/\D/g, '').slice(0, 6))} keyboardType="number-pad" maxLength={6} placeholder="000000" />
                <Button title="Verify and sign in" onPress={finishLogin} loading={busy} />
                <Pressable onPress={() => { setOtpPending(false); setOtp(''); setError(''); }} style={s.link}><Text style={s.linkText}>Use another account</Text></Pressable>
              </>}
              {error ? <Text style={s.error}>{error}</Text> : null}
            </View>
            <View style={s.security}><View style={s.dot} /><Text style={s.securityText}>Private by design · Email verified</Text></View>
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );

  return (
    <View style={s.page}>
      <StatusBar barStyle="light-content" /><LinearGradient colors={['#0b1c30', '#07111f']} style={StyleSheet.absoluteFill} />
      <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={s.header}>
          <View style={s.brandRow}><View style={s.brandMini}><Text style={s.brandMiniText}>D</Text></View><View><Text style={s.appName}>documind</Text><Text style={s.appSub}>YOUR KNOWLEDGE SPACE</Text></View></View>
          <Pressable accessibilityRole="button" accessibilityLabel="Sign out" onPress={signOut} style={s.avatar}><Text style={s.avatarText}>{username.charAt(0).toUpperCase()}</Text></Pressable>
        </View>
        <View style={s.titleRow}><View><Text style={s.eyebrow}>WELCOME BACK</Text><Text style={s.pageTitle}>{tab === 'library' ? 'Your library' : 'Ask your docs'}</Text></View>{tab === 'library' ? <Pressable onPress={upload} style={s.add}><Text style={s.addText}>＋  Add file</Text></Pressable> : null}</View>
        {error ? <Text style={s.bannerError}>{error}</Text> : null}
        <ScrollView contentContainerStyle={s.content} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => token && refresh(token, true)} tintColor={C.teal} />} keyboardShouldPersistTaps="handled">
          {tab === 'library' ? <>
            <LinearGradient colors={['#1c4560', '#17354e', '#17263c']} style={s.hero}>
              <Text style={s.heroKicker}>A LITTLE MORE CLARITY</Text><Text style={s.heroTitle}>Ask the details.{'\n'}Keep the big picture.</Text>
              <Text style={s.heroCaption}>Your private documents, ready when you are.</Text>
              <Text style={s.heroCount}>{documents.length}  <Text style={s.heroCountLabel}>DOCUMENTS IN YOUR LIBRARY</Text></Text>
            </LinearGradient>
            <View style={s.section}><View><Text style={s.sectionTitle}>Recent documents</Text><Text style={s.sectionSub}>Tap a ready file to start a conversation</Text></View>{refreshing ? <ActivityIndicator color={C.teal} /> : null}</View>
            {documents.length === 0 ? <View style={s.empty}><Text style={s.emptyIcon}>↗</Text><Text style={s.emptyTitle}>Your library starts here</Text><Text style={s.emptyCopy}>Add a PDF or TXT file and DocuMind will prepare it for questions.</Text><Button title="Upload a document" onPress={upload} loading={busy} /></View>
              : documents.map((doc) => <DocumentCard key={doc.id} item={doc} selected={selectedId === doc.id} onPress={() => { setSelectedId(doc.id); setAnswer(null); if (doc.status === 'ready') setTab('ask'); }} />)}
            <Text style={s.footer}>Documents and answers are only visible to your account.</Text>
          </> : <>
            <View style={s.askIntro}><Text style={s.askIcon}>✳</Text><View style={s.flex}><Text style={s.askTitle}>Grounded in your files</Text><Text style={s.askCopy}>Answers include source documents and page references when available.</Text></View></View>
            <Text style={s.label}>CHOOSE A DOCUMENT</Text>
            {documents.filter((d) => d.status === 'ready').length === 0
              ? <View style={s.empty}><Text style={s.emptyTitle}>No documents ready yet</Text><Text style={s.emptyCopy}>Upload a file and give it a moment to process.</Text><Button title="Go to library" onPress={() => setTab('library')} /></View>
              : <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.pills}>{documents.filter((d) => d.status === 'ready').map((doc) => <Pressable key={doc.id} onPress={() => { setSelectedId(doc.id); setAnswer(null); }} style={[s.pill, selectedId === doc.id && s.pillActive]}><Text style={s.pillIcon}>▤</Text><Text numberOfLines={1} style={[s.pillText, selectedId === doc.id && s.pillTextActive]}>{doc.display_name || fileName(doc.file)}</Text></Pressable>)}</ScrollView>}
            {selected?.status === 'ready' ? <View style={s.questionCard}><Text style={s.label}>WHAT WOULD YOU LIKE TO KNOW?</Text><TextInput value={question} onChangeText={setQuestion} placeholder="Ask about a key idea, date, or detail…" placeholderTextColor="#72849b" style={s.questionInput} multiline maxLength={2000} returnKeyType="send" onSubmitEditing={ask} /><View style={s.askActions}><Text style={s.charCount}>{question.length}/2000</Text><Button title="Ask DocuMind  →" onPress={ask} loading={busy} disabled={!question.trim()} /></View></View> : null}
            {answer ? <AnswerCard answer={answer} /> : null}
          </>}
        </ScrollView>
        <View style={s.tabs}><Tab title="Library" icon="▤" active={tab === 'library'} onPress={() => setTab('library')} /><Tab title="Ask" icon="✳" active={tab === 'ask'} onPress={() => setTab('ask')} /></View>
      </KeyboardAvoidingView>
    </View>
  );
}

function Field(props: React.ComponentProps<typeof TextInput> & { label: string }) {
  const { label, ...input } = props;
  return <View style={s.field}><Text style={s.label}>{label}</Text><TextInput {...input} style={s.textInput} placeholderTextColor="#70839b" /></View>;
}

function Button({ title, onPress, loading = false, disabled = false }: { title: string; onPress: () => void; loading?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" onPress={onPress} disabled={loading || disabled} style={({ pressed }) => [s.button, (pressed || disabled) && s.buttonPressed]}>{loading ? <ActivityIndicator color={C.bg} /> : <Text style={s.buttonText}>{title}</Text>}</Pressable>;
}

function DocumentCard({ item, selected, onPress }: { item: DocumentItem; selected: boolean; onPress: () => void }) {
  const color = item.status === 'ready' ? C.teal : item.status === 'failed' ? C.danger : C.blue;
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [s.docCard, selected && s.docCardSelected, pressed && s.pressed]}>
    <View style={s.fileIcon}><Text style={s.fileIconText}>{fileName(item.file).toLowerCase().endsWith('.pdf') ? 'PDF' : 'TXT'}</Text></View>
    <View style={s.flex}><Text numberOfLines={1} style={s.docName}>{item.display_name || fileName(item.file)}</Text><Text style={s.docMeta}>Added {new Date(item.uploaded_at).toLocaleDateString()}</Text>{item.status === 'failed' && item.processing_error ? <Text numberOfLines={2} style={s.error}>{item.processing_error}</Text> : null}</View>
    <View style={s.status}><View style={[s.dot, { backgroundColor: color }]} /><Text style={[s.statusText, { color }]}>{item.status}</Text></View>
  </Pressable>;
}

function AnswerCard({ answer }: { answer: AnswerResult }) {
  return <View style={s.answerCard}><View style={s.answerHeader}><Text style={s.askIcon}>✳</Text><Text style={s.answerEyebrow}>DOCUMIND ANSWER</Text><Text style={s.answerId}>#{answer.answer_id}</Text></View><Text style={s.questionEcho}>{answer.question}</Text><Text selectable style={s.answerText}>{answer.answer}</Text>
    {answer.sources.length ? <View style={s.sources}><Text style={s.label}>SOURCES</Text>{answer.sources.map((source, i) => <View key={source.document_title + i} style={s.sourceRow}><Text style={s.sourceBadge}>S{i + 1}</Text><Text style={s.sourceText}>{source.document_title}{source.page_number ? ' · page ' + source.page_number : ''}</Text></View>)}</View> : <Text style={s.noSources}>No matching excerpts were found for this answer.</Text>}
  </View>;
}

function Tab({ title, icon, active, onPress }: { title: string; icon: string; active: boolean; onPress: () => void }) {
  return <Pressable accessibilityRole="tab" accessibilityState={{ selected: active }} onPress={onPress} style={s.tab}><Text style={[s.tabIcon, active && s.active]}>{icon}</Text><Text style={[s.tabText, active && s.active]}>{title}</Text></Pressable>;
}

function fileName(path: string) { return decodeURIComponent(path.split('/').pop() || 'Document'); }

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: C.bg }, flex: { flex: 1 }, glow: { position: 'absolute', width: 290, height: 290, borderRadius: 150, top: -110, right: -70, backgroundColor: 'rgba(73,186,207,.09)' },
  loginScroll: { flexGrow: 1, justifyContent: 'center', padding: 24, paddingVertical: 38 },
  loginCard: { width: '100%', maxWidth: 460, alignSelf: 'center', borderRadius: 30, borderWidth: 1, borderColor: 'rgba(194,220,255,.16)', backgroundColor: 'rgba(8,20,35,.82)', padding: 27, overflow: 'hidden' },
  brand: { width: 48, height: 48, borderRadius: 17, backgroundColor: C.teal, alignItems: 'center', justifyContent: 'center', marginBottom: 28, shadowColor: C.teal, shadowOpacity: .3, shadowRadius: 18, shadowOffset: { width: 0, height: 6 } }, brandText: { fontSize: 24, fontWeight: '900', color: C.bg },
  eyebrow: { color: C.teal, fontSize: 10, fontWeight: '800', letterSpacing: 2.1 }, loginTitle: { color: C.text, fontSize: 39, lineHeight: 44, fontWeight: '700', letterSpacing: -1.1, marginTop: 12 }, loginCopy: { color: C.muted, fontSize: 14, lineHeight: 22, marginTop: 12, maxWidth: 330 },
  form: { marginTop: 31, gap: 16 }, field: { gap: 8 }, label: { fontSize: 9, color: '#a7bad0', letterSpacing: 1.6, fontWeight: '800' }, textInput: { minHeight: 52, paddingHorizontal: 16, borderRadius: 14, borderWidth: 1, borderColor: C.line, backgroundColor: 'rgba(255,255,255,.045)', color: C.text, fontSize: 15 },
  button: { minHeight: 48, paddingHorizontal: 17, borderRadius: 14, backgroundColor: C.teal, alignItems: 'center', justifyContent: 'center', shadowColor: C.teal, shadowOpacity: .16, shadowRadius: 12, shadowOffset: { width: 0, height: 5 } }, buttonText: { color: C.bg, fontSize: 13, fontWeight: '800' }, buttonPressed: { opacity: .65, transform: [{ scale: .985 }] }, otpNote: { color: C.muted, fontSize: 13, lineHeight: 20 }, link: { alignItems: 'center', padding: 7 }, linkText: { color: C.blue, fontSize: 13, fontWeight: '700' }, error: { color: C.danger, fontSize: 10, lineHeight: 16 }, security: { flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: 26, paddingTop: 18, borderTopWidth: 1, borderTopColor: C.line }, securityText: { color: '#8fa2ba', fontSize: 10, flexShrink: 1 },
  header: { paddingTop: Platform.OS === 'android' ? 42 : 56, paddingHorizontal: 22, paddingBottom: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, brandRow: { flexDirection: 'row', alignItems: 'center', gap: 11 }, brandMini: { height: 39, width: 39, borderRadius: 14, backgroundColor: C.teal, justifyContent: 'center', alignItems: 'center' }, brandMiniText: { fontSize: 19, color: C.bg, fontWeight: '900' }, appName: { color: C.text, fontSize: 17, fontWeight: '800', letterSpacing: -.4 }, appSub: { color: '#7f94ad', fontSize: 8, letterSpacing: 1.4, marginTop: 2 }, avatar: { width: 39, height: 39, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(99,230,207,.38)', backgroundColor: '#163248', alignItems: 'center', justifyContent: 'center' }, avatarText: { color: C.teal, fontWeight: '800', fontSize: 15 },
  titleRow: { paddingHorizontal: 22, paddingBottom: 17, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }, pageTitle: { color: C.text, fontWeight: '700', fontSize: 27, letterSpacing: -.65, marginTop: 6 }, add: { borderWidth: 1, borderColor: 'rgba(99,230,207,.28)', backgroundColor: 'rgba(99,230,207,.08)', paddingHorizontal: 13, paddingVertical: 10, borderRadius: 13 }, addText: { color: C.teal, fontSize: 12, fontWeight: '800' }, content: { paddingHorizontal: 20, paddingBottom: 22 }, bannerError: { color: C.danger, marginHorizontal: 20, marginBottom: 9, fontSize: 12 },
  hero: { borderRadius: 23, padding: 21, minHeight: 204, overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(173,213,255,.12)' }, heroKicker: { color: '#9ccbcf', fontSize: 9, fontWeight: '800', letterSpacing: 1.8 }, heroTitle: { fontSize: 25, lineHeight: 30, letterSpacing: -.55, fontWeight: '700', color: C.text, marginTop: 10 }, heroCaption: { color: '#a9bfd0', fontSize: 11, marginTop: 8 }, heroCount: { color: C.teal, fontSize: 16, fontWeight: '900', marginTop: 17 }, heroCountLabel: { color: '#a6bbca', letterSpacing: 1.2, fontSize: 8, fontWeight: '700' },
  section: { marginTop: 27, marginBottom: 13, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700' }, sectionSub: { color: '#8499b1', fontSize: 10, marginTop: 4 }, docCard: { minHeight: 77, flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: 'rgba(16,29,46,.88)', padding: 13, marginBottom: 9, borderRadius: 17, borderWidth: 1, borderColor: C.line }, docCardSelected: { borderColor: 'rgba(99,230,207,.42)', backgroundColor: '#122b3b' }, pressed: { transform: [{ scale: .99 }], opacity: .88 }, fileIcon: { width: 42, height: 48, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(99,230,207,.12)' }, fileIconText: { color: C.teal, fontSize: 9, fontWeight: '900' }, docName: { color: C.text, fontWeight: '700', fontSize: 12 }, docMeta: { color: '#8497ad', fontSize: 9, marginTop: 5 }, status: { alignItems: 'flex-end', gap: 5, flexDirection: 'row' }, dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: C.teal }, statusText: { fontSize: 9, fontWeight: '700', textTransform: 'capitalize' },
  empty: { alignItems: 'center', padding: 22, borderWidth: 1, borderColor: C.line, borderRadius: 20, backgroundColor: 'rgba(16,29,46,.7)', gap: 11, marginTop: 10 }, emptyIcon: { color: C.teal, fontSize: 28 }, emptyTitle: { color: C.text, fontWeight: '700', fontSize: 15, textAlign: 'center' }, emptyCopy: { color: C.muted, textAlign: 'center', fontSize: 11, lineHeight: 18, marginBottom: 4, maxWidth: 280 }, footer: { color: '#74889f', fontSize: 9, textAlign: 'center', marginTop: 21, marginBottom: 8 },
  tabs: { height: 72, flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', paddingBottom: Platform.OS === 'ios' ? 12 : 3, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: '#0a1726' }, tab: { width: 100, alignItems: 'center', gap: 4, paddingVertical: 5 }, tabIcon: { color: '#71859d', fontSize: 17 }, tabText: { color: '#71859d', fontSize: 9, fontWeight: '700' }, active: { color: C.teal },
  askIntro: { flexDirection: 'row', gap: 13, padding: 17, borderRadius: 19, backgroundColor: 'rgba(20,36,58,.9)', borderWidth: 1, borderColor: C.line, marginTop: 2, marginBottom: 25 }, askIcon: { color: C.teal, fontSize: 21 }, askTitle: { color: C.text, fontSize: 14, fontWeight: '700' }, askCopy: { color: C.muted, fontSize: 10, lineHeight: 16, marginTop: 5 }, pills: { gap: 9, paddingVertical: 12 }, pill: { maxWidth: 215, flexDirection: 'row', alignItems: 'center', gap: 7, borderWidth: 1, borderColor: C.line, backgroundColor: C.panel, borderRadius: 13, paddingVertical: 11, paddingHorizontal: 12 }, pillActive: { backgroundColor: 'rgba(99,230,207,.11)', borderColor: 'rgba(99,230,207,.42)' }, pillIcon: { color: C.teal, fontSize: 13 }, pillText: { color: C.muted, fontSize: 10, fontWeight: '600', flexShrink: 1 }, pillTextActive: { color: C.text },
  questionCard: { padding: 17, marginTop: 16, backgroundColor: C.panel, borderRadius: 20, borderWidth: 1, borderColor: C.line }, questionInput: { minHeight: 100, maxHeight: 180, color: C.text, fontSize: 14, lineHeight: 22, paddingTop: 14, textAlignVertical: 'top' }, askActions: { borderTopWidth: 1, borderTopColor: C.line, paddingTop: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }, charCount: { color: '#70839b', fontSize: 9 },
  answerCard: { borderRadius: 21, borderWidth: 1, borderColor: 'rgba(99,230,207,.23)', backgroundColor: '#102236', marginTop: 20, padding: 17 }, answerHeader: { flexDirection: 'row', alignItems: 'center', gap: 7 }, answerEyebrow: { color: C.teal, fontSize: 9, fontWeight: '900', letterSpacing: 1.5, flex: 1 }, answerId: { color: '#748ba2', fontSize: 9 }, questionEcho: { color: '#92a8bd', fontSize: 10, marginTop: 13, marginBottom: 8 }, answerText: { color: C.text, fontSize: 13, lineHeight: 22 }, sources: { marginTop: 20, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 13, gap: 9 }, sourceRow: { flexDirection: 'row', alignItems: 'center', gap: 8 }, sourceBadge: { width: 24, height: 22, textAlign: 'center', textAlignVertical: 'center', borderRadius: 7, color: C.teal, backgroundColor: 'rgba(99,230,207,.12)', fontSize: 9, fontWeight: '800' }, sourceText: { color: '#b6c7d9', fontSize: 10, flex: 1 }, noSources: { color: '#8599ad', fontSize: 10, marginTop: 18 },
});
