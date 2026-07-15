<script setup>
defineProps({ type: { type: Object, required: true } })
defineEmits(['select'])
</script>

<template>
  <button class="type-card" type="button" @click="$emit('select', type.code)">
    <span class="type-icon" :class="`tone-${type.tone}`">
      <img :src="type.iconSrc" :alt="type.name" />
    </span>
    <span class="type-copy">
      <strong>{{ type.name }}</strong>
      <small>{{ type.description }}</small>
    </span>
    <span class="arrow" aria-hidden="true">›</span>
  </button>
</template>

<style scoped>
.type-card {
  width: 100%;
  min-height: 118px;
  padding: 20px 22px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 17px;
  text-align: left;
  color: var(--navy);
  background: rgba(255,255,255,.82);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 8px 26px rgba(35,52,43,.045);
  transition: transform 160ms, border-color 160ms, box-shadow 160ms;
}

.type-card:hover {
  transform: translateY(-3px);
  border-color: #b6d1be;
  box-shadow: var(--shadow);
}

.type-icon {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 29px;
  flex-shrink: 0;
}

.type-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.tone-green { background: #e5f3d9; }
.tone-blue { background: #e7f1fb; }
.tone-purple { background: #f1ebf6; }
.tone-orange { background: #fff0dc; }

.type-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.type-copy strong {
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: -.45px;
}

.type-copy small {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
  letter-spacing: -.2px;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: keep-all;
}

.arrow {
  color: var(--green-900);
  font-size: 30px;
  font-weight: 300;
  flex-shrink: 0;
}

@media (max-width: 560px) {
  .type-card {
    min-height: 96px;
    padding: 15px;
  }

  .type-icon {
    width: 54px;
    height: 54px;
    font-size: 24px;
  }

  .type-copy small {
    font-size: 12px;
  }
}
</style>