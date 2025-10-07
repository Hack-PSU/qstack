import { useState } from "react";
import { Button, Container, Title, Text, Paper, Stack, Center } from "@mantine/core";
import { IconBrandDiscord } from "@tabler/icons-react";

export default function ConnectDiscord() {
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnectDiscord = () => {
    setIsConnecting(true);
    // Redirect to Discord OAuth login
    window.location.href = "/api/auth/discord/login";
  };

  return (
    <Container size="sm" py="6rem">
      <Paper p="xl" shadow="xs" className="bg-neutral-800">
        <Stack gap="xl" align="center">
          <IconBrandDiscord size={64} color="#5865F2" />

          <Title order={2} ta="center">
            Connect Your Discord Account
          </Title>

          <Text ta="center" c="dimmed">
            To use QStack, you need to connect your Discord account.
            This allows mentors and organizers to reach you for help.
          </Text>

          <Center>
            <Button
              leftSection={<IconBrandDiscord size={20} />}
              size="lg"
              color="indigo"
              onClick={handleConnectDiscord}
              loading={isConnecting}
              disabled={isConnecting}
              fullWidth
            >
              Connect Discord
            </Button>
          </Center>

          <Text ta="center" size="xs" c="dimmed">
            You'll be redirected to Discord to authorize QStack
          </Text>
        </Stack>
      </Paper>
    </Container>
  );
}
