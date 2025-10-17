import { useState } from "react";
import { Button, Container, Title, Text, Paper, Stack, Center, TextInput, Divider } from "@mantine/core";
import { IconBrandDiscord, IconPhone } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";

export default function ConnectDiscord() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [isSubmittingPhone, setIsSubmittingPhone] = useState(false);

  const handleConnectDiscord = () => {
    setIsConnecting(true);
    // Redirect to Discord OAuth login
    window.location.href = "/api/auth/discord/login";
  };

  const handleSubmitPhone = async () => {
    if (!phoneNumber.trim()) {
      notifications.show({
        title: "Error",
        message: "Please enter a valid phone number",
        color: "red",
      });
      return;
    }

    setIsSubmittingPhone(true);
    try {
      const response = await fetch("/api/auth/set-phone", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ phone: phoneNumber }),
      });

      const data = await response.json();

      if (data.success) {
        notifications.show({
          title: "Success",
          message: "Phone number saved successfully!",
          color: "green",
        });
        // Redirect to home after successful phone submission
        setTimeout(() => {
          window.location.href = "/home";
        }, 1000);
      } else {
        notifications.show({
          title: "Error",
          message: data.error || "Failed to save phone number",
          color: "red",
        });
      }
    } catch (error) {
      notifications.show({
        title: "Error",
        message: "Failed to save phone number",
        color: "red",
      });
    } finally {
      setIsSubmittingPhone(false);
    }
  };

  return (
    <Container size="sm" py="6rem">
      <Paper p="xl" shadow="xs" className="bg-neutral-800">
        <Stack gap="xl" align="center">
          <IconBrandDiscord size={64} color="#5865F2" />

          <Title order={2} ta="center">
            Connect Your Contact Information
          </Title>

          <Text ta="center" c="dimmed">
            To use QStack, you need to provide contact information.
            This allows mentors and organizers to reach you for help.
          </Text>

          <Center w="100%">
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

          <Divider label="OR" labelPosition="center" w="100%" />

          <Stack gap="md" w="100%">
            <Text ta="center" c="dimmed" size="sm">
              Prefer not to use Discord? Provide your phone number instead:
            </Text>

            <TextInput
              leftSection={<IconPhone size={20} />}
              placeholder="Enter your phone number"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.currentTarget.value)}
              size="md"
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleSubmitPhone();
                }
              }}
            />

            <Button
              size="lg"
              color="teal"
              onClick={handleSubmitPhone}
              loading={isSubmittingPhone}
              disabled={isSubmittingPhone || !phoneNumber.trim()}
              fullWidth
            >
              Submit Phone Number
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Container>
  );
}
