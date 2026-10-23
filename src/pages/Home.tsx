export default function Home() {
  return (
    <div className="animate-fade-in w-full bg-white pb-16">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Top Header Logos */}
        <div className="flex flex-col items-center justify-center py-10 text-center select-none border-b border-slate-100">
          <img 
            src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg" 
            alt="National Emblem" 
            className="h-24 mb-4 object-contain" 
          />
          <h2 className="text-xl md:text-2xl font-bold text-slate-800 tracking-[0.2em] uppercase">भारत सरकार</h2>
          <p className="text-xs md:text-sm font-semibold tracking-[0.3em] text-slate-600 mb-2 uppercase">Bharat Sarkar / Government of India</p>
          <h1 className="text-2xl md:text-3xl font-black text-slate-900 tracking-[0.15em] uppercase">Ministry of Defence</h1>
        </div>

        {/* Hero Banner Grid (Now taller and explicit heights) */}
        <div className="mt-8 rounded-2xl overflow-hidden bg-white shadow-xl border border-slate-200">
          <div className="grid grid-cols-1 lg:grid-cols-2">
            {/* Main Text Content in Hero */}
            <div className="p-8 md:p-12 lg:p-16 flex flex-col justify-center bg-slate-50 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/5 rounded-full blur-3xl"></div>
              
              <span className="inline-block px-4 py-1.5 rounded-full bg-orange-100 text-orange-700 font-bold text-xs tracking-widest uppercase mb-6 w-max border border-orange-200">
                IBVAP Core System
              </span>

              <h2 className="text-3xl md:text-4xl lg:text-5xl font-black text-slate-900 mb-6 tracking-tight leading-tight">
                Intelligent Border <span className="text-orange-600">Surveillance</span> & Intrusion Detection
              </h2>
              
              <p className="text-base md:text-lg font-semibold text-slate-600 mb-8 leading-relaxed max-w-xl">
                A fully automated, advanced AI-driven CCTV detection system designed exclusively for the Indian Army and Government. Monitor borders 24/7, detect threats instantly, and safeguard the nation.
              </p>

              <div className="inline-flex items-center gap-3 text-sm font-bold text-slate-600 tracking-widest uppercase">
                <span className="w-12 h-[2px] bg-slate-300"></span>
                Secure Command Operations
              </div>
            </div>

            {/* Main Image (Explicit height to prevent disappearing) */}
            <div className="h-[400px] lg:h-auto min-h-[400px] bg-slate-200 relative">
              <img 
                src="/border_patrol.jpg" 
                alt="Border Security Patrol" 
                className="absolute inset-0 w-full h-full object-cover object-center"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent"></div>
              <div className="absolute bottom-6 left-6 right-6">
                <p className="text-white font-bold tracking-widest uppercase text-sm">Northern Command Sector</p>
                <div className="h-1 w-16 bg-orange-500 mt-2"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Extended Informational Blocks (To make page scrollable) */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <div className="bg-white p-8 md:p-10 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
             <div className="w-12 h-12 bg-orange-50 rounded-xl flex items-center justify-center mb-6 border border-orange-100">
               <span className="text-orange-600 font-bold text-xl">01</span>
             </div>
             <h3 className="text-2xl font-black text-slate-900 mb-4 tracking-wide">
               उन्नत एआई-संचालित निगरानी (Advanced AI Monitoring)
             </h3>
             <p className="text-slate-600 font-medium leading-loose text-justify mb-4">
               हमारा प्लेटफ़ॉर्म अत्याधुनिक कृत्रिम बुद्धिमत्ता (Artificial Intelligence) और मशीन लर्निंग एल्गोरिदम का उपयोग करता है। यह सिस्टम लाइव सीसीटीवी फीड का विश्लेषण करके किसी भी प्रकार की संदिग्ध गतिविधि या घुसपैठ का सटीक और तेजी से पता लगाने में सक्षम है। 
             </p>
             <p className="text-slate-600 font-medium leading-loose text-justify">
               सिस्टम दिन और रात (Thermal/Night Vision), हर मौसम में काम करने के लिए डिज़ाइन किया गया है। यह सिर्फ लोगों की ही नहीं, बल्कि वाहनों की नंबर प्लेट (ANPR) और हथियारों की भी पहचान कर सकता है, जिससे हमारे सुरक्षा बलों को तुरंत अलर्ट मिल सके।
             </p>
          </div>

          <div className="bg-white p-8 md:p-10 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
             <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center mb-6 border border-green-100">
               <span className="text-green-600 font-bold text-xl">02</span>
             </div>
             <h3 className="text-2xl font-black text-slate-900 mb-4 tracking-wide">
               केंद्रीकृत रक्षा नियंत्रण (Centralized Control)
             </h3>
             <p className="text-slate-600 font-medium leading-loose text-justify mb-4">
               देश की सीमाओं पर तैनात हजारों कैमरों का पूरा नियंत्रण एक सेंट्रलाइज्ड डैशबोर्ड के जरिए किया जाता है। अधिकारी किसी भी समय, किसी भी सेक्टर (जैसे नॉर्दर्न कमांड, ईस्टर्न कमांड) की लाइव फुटेज देख सकते हैं और अलर्ट्स को मैनेज कर सकते हैं।
             </p>
             <p className="text-slate-600 font-medium leading-loose text-justify">
               यह डेटा पूरी तरह से सुरक्षित (End-to-End Encrypted) और रक्षा मंत्रालय के कड़े सुरक्षा मानकों (Ministry of Defence Security Protocols) का पालन करते हुए भारतीय सर्वर पर ही स्टोर किया जाता है।
             </p>
          </div>

        </div>

        {/* Motivational Banner / Quote */}
        <div className="mt-12 bg-slate-900 rounded-2xl p-10 md:p-16 text-center relative overflow-hidden shadow-2xl">
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1600&q=80')] bg-cover bg-center opacity-10"></div>
          
          <div className="relative z-10 max-w-4xl mx-auto">
            <svg className="w-12 h-12 text-orange-500 mx-auto mb-6 opacity-80" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
            </svg>
            <h2 className="text-3xl md:text-5xl font-black text-white italic mb-6 leading-tight">
              “वीर भोग्या वसुंधरा” 
            </h2>
            <p className="text-lg md:text-xl font-bold text-orange-400 mb-8 uppercase tracking-[0.2em]">
              (The Brave Shall Inherit The Earth)
            </p>
            <p className="text-base md:text-lg font-medium text-slate-700 leading-title max-w-2xl mx-auto">
              देश की सुरक्षा में तैनात हर सिपाही का समर्पण और हमारी एआई तकनीक का संगम। हम सीमाओं को अभेद्य बनाने के लिए प्रतिबद्ध हैं। जय हिंद!
            </p>
          </div>
        </div>

        {/* 3 Grid Images at bottom (Explicit sizing) */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-64 sm:h-72 rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative group">
            <img src="/special_forces.jpg" alt="Special Forces" className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
            <p className="absolute bottom-4 left-4 text-white font-bold tracking-widest uppercase text-sm">Tactical Response</p>
          </div>
          <div className="h-64 sm:h-72 rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative group">
            <img src="/border_fence.jpg" alt="Border Fencing" className="absolute inset-0 w-full h-full object-cover grayscale transition-transform duration-700 group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
            <p className="absolute bottom-4 left-4 text-white font-bold tracking-widest uppercase text-sm">Virtual Fencing</p>
          </div>
          <div className="h-64 sm:h-72 rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative group">
            <img src="/live_feed.jpg" alt="Live Feed" className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
            <p className="absolute bottom-4 left-4 text-white font-bold tracking-widest uppercase text-sm">Live Surveillance Feed</p>
          </div>
        </div>
        
      </div>
    </div>
  );
}
