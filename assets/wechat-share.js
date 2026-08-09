(() => {
  "use strict";

  if (!/MicroMessenger/i.test(navigator.userAgent)) {
    return;
  }

  const signerUrl = "https://d3dp3fxu4p4bho.cloudfront.net/sign";
  const canonicalUrl = "https://www.qinzy.tech/";
  const title = "Zengyi Qin - AI Researcher";
  const description =
    "Zengyi Qin is an AI Researcher, MIT PhD, and Multi-modal Agents Eval Lead at Meta Superintelligence Labs.";
  const imageUrl = "https://www.qinzy.tech/assets/wechat-share.jpg";
  const pageUrl = window.location.href.split("#", 1)[0];

  const loadSdk = new Promise((resolve, reject) => {
    if (window.wx) {
      resolve(window.wx);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://res.wx.qq.com/open/js/jweixin-1.6.0.js";
    script.async = true;
    script.onload = () => resolve(window.wx);
    script.onerror = () => reject(new Error("Unable to load the WeChat JS-SDK"));
    document.head.appendChild(script);
  });

  const loadSignature = fetch(`${signerUrl}?url=${encodeURIComponent(pageUrl)}`, {
    headers: { Accept: "application/json" },
    mode: "cors",
  }).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Unable to load the WeChat signature");
    }
    return payload;
  });

  Promise.all([loadSdk, loadSignature])
    .then(([wx, signature]) => {
      wx.config({
        debug: false,
        appId: signature.appId,
        timestamp: signature.timestamp,
        nonceStr: signature.nonceStr,
        signature: signature.signature,
        jsApiList: ["updateAppMessageShareData", "updateTimelineShareData"],
      });

      wx.ready(() => {
        wx.updateAppMessageShareData({
          title,
          desc: description,
          link: canonicalUrl,
          imgUrl: imageUrl,
        });
        wx.updateTimelineShareData({
          title,
          link: canonicalUrl,
          imgUrl: imageUrl,
        });
      });

      wx.error((error) => {
        console.warn("WeChat share configuration failed", error);
      });
    })
    .catch((error) => {
      console.warn("WeChat share setup failed", error);
    });
})();
