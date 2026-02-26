// Debug script to check localStorage and conversation loading
console.log('=== AI Assistant History Debug ===');

// Check localStorage
try {
  const stored = localStorage.getItem('ai_chat_history');
  if (stored) {
    const data = JSON.parse(stored);
    console.log('✅ Found stored history');
    console.log('Conversations:', data.conversations?.length || 0);
    console.log('Current ID:', data.currentConversationId);

    if (data.conversations && data.conversations.length > 0) {
      console.log('\nFirst conversation:');
      console.log('  ID:', data.conversations[0].id);
      console.log('  Title:', data.conversations[0].title);
      console.log('  Messages:', data.conversations[0].messages?.length || 0);
      console.log('  Created:', data.conversations[0].createdAt);
      console.log('  Updated:', data.conversations[0].updatedAt);
    }
  } else {
    console.log('❌ No history found in localStorage');
  }
} catch (e) {
  console.error('❌ Error reading localStorage:', e);
}

console.log('\n=== End Debug ===');
