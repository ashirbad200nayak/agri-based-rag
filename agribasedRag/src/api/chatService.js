const API_URL = import.meta.env.PROD 
  ? "/api/chat" 
  : "http://localhost:8000/api/chat";

export const sendMessage = async (message, region = null) => {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, region }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to send message:", error);
    throw error;
  }
};
