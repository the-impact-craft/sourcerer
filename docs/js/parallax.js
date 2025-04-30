window.addEventListener("DOMContentLoaded", () => {
  console.log("DOMContentLoaded");
})


window.addEventListener('scroll', (event) => {
    // Check if the current page is the home page
    console.log("window.location.pathname");
    console.log(event);
    const scrollY = window.scrollY;

    const layer1 = document.querySelector('.layer-1');  // sky
    const layer2 = document.querySelector('.layer-2');  // mountains
    const layer3 = document.querySelector('.layer-3');  // bush
    const layer4 = document.querySelector('.layer-4');  // wizard
    const layer5 = document.querySelector('.layer-5');  // clouds


    if (layer1) layer1.style.transform = `translateY(${scrollY * 0.1}px)`;
    if (layer2) layer2.style.transform = `translateY(${scrollY * 0.5}px)`;
    if (layer3) layer3.style.transform = `translateY(${scrollY * 0.2}px)`;
    if (layer4) layer4.style.transform = `translateY(${scrollY * 0.2}px)`;
    if (layer5) layer5.style.transform = `translateY(${scrollY * 0.5}px)`;
  });

toggleVisibility = () => {
   console.log('Do your thg');
};

const AppWrapper = document.getElementById('app');
AppWrapper.addEventListener('scroll', toggleVisibility);


