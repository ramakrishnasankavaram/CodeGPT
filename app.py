import streamlit as st
import google.generativeai as genai  # Google AI API
from PIL import Image  # For image handling

# 🔑 Set Your Google AI API Key (Replace with Your Key)
GOOGLE_API_KEY = "AIzaSyBChtpfxdTTuHGV_UY1-i6EpBhC03-1K1M"
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="CodeGPT - AI Debugger", page_icon="🧑‍💻")
# 🎨 Custom Styling for UI
st.markdown("""
    <style>
        body {background-color: #f8f9fa;}
        .stTextInput, .stTextArea, .stButton>button {
            border-radius: 10px;
            font-size: 18px;
        }
        .stButton>button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
        }
        .stButton>button:hover {
            background-color: #0056b3;
        }
    </style>
""", unsafe_allow_html=True)

# 🏆 Title & Introduction
st.markdown("<h1 style='text-align: center; color: #007bff;'>✨ CODE GPT ✨</h1>", unsafe_allow_html=True)
st.markdown("#### 🚀 Empower Your Coding with AI | Debug • Explain • Optimize")

# 🎯 Sidebar for Feature Selection
st.sidebar.image("Logo.webp", width=250)
st.sidebar.markdown("## Choose Features")

# 📝 User Input for Code
code_input = st.text_area("📝 Paste Your Code Here:", height=200)

# 🔍 Multi-Feature Selection with Checkboxes
features_selected = []
features = {
    "Find & Fix Bugs": st.sidebar.checkbox("Find & Fix Bugs"),
    "Explain Code": st.sidebar.checkbox("Explain Code"),
    "Convert Handwritten Code": st.sidebar.checkbox("Convert Handwritten Code"),
    "Optimize Code": st.sidebar.checkbox("Optimize Code"),
    "Detect & Adapt Language": st.sidebar.checkbox("Detect & Adapt Language"),
    "Refactor Code": st.sidebar.checkbox("Refactor Code"),
}

# Store selected features
for feature, selected in features.items():
    if selected:
        features_selected.append(feature)

uploaded_file = None
extracted_text = None

if "Convert Handwritten Code" in features_selected:
    uploaded_file = st.file_uploader("📸 Upload Handwritten Code Image", type=["png", "jpg", "jpeg"])

# 📌 Function to Call Google AI API (Gemini)
def query_gemini(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")  # Using Google's AI Model
    response = model.generate_content(prompt)
    return response.text
def reply(input,image,prompt):
    model1 = genai.GenerativeModel("gemini-1.5-pro")
    response=model1.generate_content([input,image,prompt])
    return response.text

# 🚀 Process All Selected Features
if st.button("✨ Process with AI"):
    if not features_selected:
        prompt=f"""
        Make the heading as Finding & Fixing Bugs
        Analyze the following code for errors and potential bugs. Identify syntax issues, logical errors, and performance inefficiencies. 
                                Provide a list of errors with explanations and suggest fixes. give headings in bold text.If there are no errors, mention that there are no errors.
                                Code:{code_input}
                                Output Format:
                                - Bug Type
                                - Issue: Describe the problem.
                                - Suggested Fix: Provide a corrected version of the code.
                                - Explanation: Explain why the fix works.

        Make the heading as Explaination of Code
        Explain the following code in simple terms. Break it down step by step, describing what each function, loop, and condition does. 
                            Provide a beginner-friendly explanation, highlighting variable interactions and purpose.give headings in bold text.

                            Code:
                            {code_input}

                            Output Format:
                            - Overview: What the code does.
                            - Step-by-Step Breakdown: Explain each important line.
                            - Key Concepts Used: List algorithms, data structures, and logic patterns.

        Make the heading as Optimizing Code
        Optimize the following code to improve time and space efficiency. Identify inefficiencies and suggest improvements while maintaining the same functionality. 
                            If there are redundant lines, suggest their removal.please give headings in bold text. 

                            Code:
                            {code_input}

                            Output Format:
                            - Current Issues: Describe inefficiencies in time/space complexity.
                            - Optimized Code:
                            - Explanation of Improvements:
                            - Before & After Performance (if applicable)

        
        Make the heading as Detect & Adapt Language
        Detect the programming language of the following code. If it is Python, JavaScript, C++, Java, or Ruby, and go provide equivalent implementations in the other languages.

                        Code:
                        {code_input}

                        Output Format:
                        - Detected Language:
                        - Equivalent Implementations in Other Languages:

        
        Make the heading as Refactoring the Code
        Refactor the following code to enhance readability, maintainability, and structure. Improve variable naming, break down large functions, and eliminate redundant code while preserving functionality.  
                Format the output with bold headings.  

                Code:  
                {code_input}  

                Expected Output:  
                - Refactored Code:  
                - Key Improvements:  
                - **How These Changes Enhance Readability:

        """
        output=query_gemini(prompt)
        st.success("✨ AI Processed Your Code!")
        st.markdown(output, unsafe_allow_html=True)

    else:
        for feature in features_selected:
            if feature == "Convert Handwritten Code" and uploaded_file:
                image1 = Image.open(uploaded_file)
                st.image(image1)
                prompt="i provide you a image contaning hand written code . you need to analyze the image and generate the handwritten code as noraml digital code and provide the explantion for the code and there any errors fix it otherswise leave and if no text found in image give as no text found"

                # 🛠 Extract text from image using Pytesseract with better accuracy settings
                extracted_text = reply("",image1,prompt)
                st.write(extracted_text)



                    

            elif feature == "Find & Fix Bugs":
                prompt = f"""Analyze the following code for errors and potential bugs. Identify syntax issues, logical errors, and performance inefficiencies. 
                                Provide a list of errors with explanations and suggest fixes. give headings in bold text.If there are no errors, mention that there are no errors.
                                Code:{code_input}
                                Output Format:
                                - Bug Type
                                - Issue: Describe the problem.
                                - Suggested Fix: Provide a corrected version of the code.
                                - Explanation: Explain why the fix works."""
                output = query_gemini(prompt)
                st.success("✅ AI Debugged Your Code!")
                st.markdown(output, unsafe_allow_html=True)

            elif feature == "Explain Code":
                prompt = f"""Explain the following code in simple terms. Break it down step by step, describing what each function, loop, and condition does. 
                            Provide a beginner-friendly explanation, highlighting variable interactions and purpose.give headings in bold text.

                            Code:
                            {code_input}

                            Output Format:
                            - Overview: What the code does.
                            - Step-by-Step Breakdown: Explain each important line.
                            - Key Concepts Used: List algorithms, data structures, and logic patterns.
                            """
                output = query_gemini(prompt)
                st.info("📚 AI Explanation:")
                st.markdown(output, unsafe_allow_html=True)


            elif feature == "Optimize Code":
                prompt = f"""Optimize the following code to improve time and space efficiency. Identify inefficiencies and suggest improvements while maintaining the same functionality. 
                            If there are redundant lines, suggest their removal.please give headings in bold text. 

                            Code:
                            {code_input}

                            Output Format:
                            - Current Issues: Describe inefficiencies in time/space complexity.
                            - Optimized Code:
                            - Explanation of Improvements:
                            - Before & After Performance (if applicable):
                            """
                output = query_gemini(prompt)
                st.success("⚡ AI Optimized Your Code!")
                st.markdown(output, unsafe_allow_html=True)

            elif feature == "Detect & Adapt Language":
                prompt = f"""Detect the programming language of the following code. If it is Python, JavaScript, C++, Java, or Ruby, and go provide equivalent implementations in the other languages.

                        Code:
                        {code_input}

                        Output Format:
                        - Detected Language:
                        - Equivalent Implementations in Other Languages:
                        """
                output = query_gemini(prompt)
                st.info("🌎 AI Detected & Adapted Code:")
                st.markdown(output, unsafe_allow_html=True)

            elif feature == "Refactor Code":
                prompt = f"""Refactor the following code to enhance readability, maintainability, and structure. Improve variable naming, break down large functions, and eliminate redundant code while preserving functionality.  
                Format the output with bold headings.  

                Code:  
                {code_input}  

                Expected Output:  
                - Refactored Code:  
                - Key Improvements:  
                - How These Changes Enhance Readability:  
                """
                output = query_gemini(prompt)
                st.success("🔄 AI Refactored Your Code!")
                st.markdown(output, unsafe_allow_html=True)
        

# 📌 Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>🚀 Created by TEAM ARJUNA</p>", unsafe_allow_html=True)
