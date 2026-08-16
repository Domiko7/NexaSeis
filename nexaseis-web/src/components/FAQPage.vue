<script setup lang="ts">
defineEmits<{
  back: [];
}>();

const faqItems = [
  {
    question: "Why does it say (2026-2030) on your fdsn page?",
    answer: "Our network does not meet the requirements for a permament network, thus we had to put something and the date is a placeholder. It's also important to keep in mind that this is a side project and the servers won't be turned on forerver, however if we do ever turn them off there will be a lot of notices and tutorials how to host the server on your own (it's lightweight).",
  },
  {
    question: "Can I join NexaSeis' network?",
    answer: "Yes, you can! To add your station to the network, reach out to me via my discord server (https://discord.domiko.dev) or email me (mail@domiko.dev). If you haven't build one yet, check out our official tutorial! https://domiko.dev/blog/diy-seismometer Adding raspberry shakes and anyshake is possible aswell.",
  },
  {
    question: "Can I host NexaSeis myself?",
    answer: "Yes, you can! Clone the github repository (https://github.com/Domiko7/NexaSeis) and edit the config.json.",
  },
  {
    question: "How do I access NexaSeis' seedlink?",
    answer: "As of now the seedlink isn't fully public yet however if you want it reach out to me via my discord server (https://discord.domiko.dev) or email me (mail@domiko.dev). We're also working on improving the website and getting our data into iris' seedlink. ",
  },
];
</script>

<template>
  <v-main class="faq-page-wrapper">
    <section class="faq-page" aria-labelledby="faq-heading">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="$emit('back')">
        Back to home
      </v-btn>
      <h1 id="faq-heading">Frequently asked questions</h1>
      <v-expansion-panels variant="accordion">
        <v-expansion-panel
          v-for="item in faqItems"
          :key="item.question"
          :title="item.question"
          :text="item.answer"
        />
      </v-expansion-panels>
    </section>
  </v-main>
</template>

<style scoped>
.faq-page-wrapper {
  width: 100%;
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: clamp(40px, 7vh, 76px) 20px;
  background: #0a2632;
}

.faq-page {
  width: min(100%, 760px);
  text-align: left;
}

.faq-page h1 {
  margin: 30px 0;
  text-align: center;
  font-size: clamp(36px, 6vw, 56px);
  line-height: 1.05;
}
</style>
